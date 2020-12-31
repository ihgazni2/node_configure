from __future__ import print_function

import os
import pprint
import subprocess
import shlex
import re
import shutil
import bz2
import io
import json
import sys
import errno

import getmoduleversion
import getnapibuildversion
from distutils.spawn import find_executable as which
from distutils.version import StrictVersion
import nodedownload

CC = os.environ.get('CC', 'cc' if sys.platform == 'darwin' else 'gcc')
CXX = os.environ.get('CXX', 'c++' if sys.platform == 'darwin' else 'g++')



def error(msg):
    prefix = '\033[1m\033[31mERROR\033[0m' if os.isatty(1) else 'ERROR'
    print('%s: %s' % (prefix, msg))
    sys.exit(1)


def warn(msg):
    warn.warned = True
    prefix = '\033[1m\033[93mWARNING\033[0m' if os.isatty(1) else 'WARNING'
    print('%s: %s' % (prefix, msg))

warn.warned = False


def info(msg):
    prefix = '\033[1m\033[32mINFO\033[0m' if os.isatty(1) else 'INFO'
    print('%s: %s' % (prefix, msg))


def print_verbose(x,options):
    if not options.verbose:
        return
    if type(x) is str:
        print(x)
    else:
        pprint.pprint(x, indent=2)


def b(value):
    """Returns the string 'true' if value is truthy, 'false' otherwise."""
    return 'true' if value else 'false'

def B(value):
    """Returns 1 if value is truthy, 0 otherwise."""
    return 1 if value else 0


def to_utf8(s):
    return s if isinstance(s, str) else s.decode("utf-8")


def pkg_config(pkg):
  """Run pkg-config on the specified package
  Returns ("-l flags", "-I flags", "-L flags", "version")
  otherwise (None, None, None, None)"""
  pkg_config = os.environ.get('PKG_CONFIG', 'pkg-config')
  args = []  # Print pkg-config warnings on first round.
  retval = ()
  for flag in ['--libs-only-l', '--cflags-only-I',
               '--libs-only-L', '--modversion']:
    args += [flag]
    if isinstance(pkg, list):
      args += pkg
    else:
      args += [pkg]
    try:
      proc = subprocess.Popen(shlex.split(pkg_config) + args,
                              stdout=subprocess.PIPE)
      val = to_utf8(proc.communicate()[0]).strip()
    except OSError as e:
      if e.errno != errno.ENOENT: raise e  # Unexpected error.
      return (None, None, None, None)  # No pkg-config/pkgconf installed.
    retval += (val,)
    args = ['--silence-errors']
  return retval


def try_check_compiler(cc, lang):
  try:
    proc = subprocess.Popen(shlex.split(cc) + ['-E', '-P', '-x', lang, '-'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  except OSError:
    return (False, False, '', '')

  proc.stdin.write(b'__clang__ __GNUC__ __GNUC_MINOR__ __GNUC_PATCHLEVEL__ '
                   b'__clang_major__ __clang_minor__ __clang_patchlevel__')

  values = (to_utf8(proc.communicate()[0]).split() + ['0'] * 7)[0:7]
  is_clang = values[0] == '1'
  gcc_version = tuple(map(int, values[1:1+3]))
  clang_version = tuple(map(int, values[4:4+3])) if is_clang else None

  return (True, is_clang, clang_version, gcc_version)



def get_version_helper(cc, regexp):
  try:
    proc = subprocess.Popen(shlex.split(cc) + ['-v'], stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE, stdout=subprocess.PIPE)
  except OSError:
    error('''No acceptable C compiler found!
       Please make sure you have a C compiler installed on your system and/or
       consider adjusting the CC environment variable if you installed
       it in a non-standard prefix.''')

  match = re.search(regexp, to_utf8(proc.communicate()[1]))

  if match:
    return match.group(2)
  else:
    return '0.0'



def get_nasm_version(asm):
  try:
    proc = subprocess.Popen(shlex.split(asm) + ['-v'],
                            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)
  except OSError:
    warn('''No acceptable ASM compiler found!
         Please make sure you have installed NASM from https://www.nasm.us
         and refer BUILDING.md.''')
    return '0.0'

  match = re.match(r"NASM version ([2-9]\.[0-9][0-9]+)",
                   to_utf8(proc.communicate()[0]))

  if match:
    return match.group(1)
  else:
    return '0.0'


def get_llvm_version(cc):
  return get_version_helper(
    cc, r"(^(?:.+ )?clang version|based on LLVM) ([0-9]+\.[0-9]+)")

def get_xcode_version(cc):
  return get_version_helper(
    cc, r"(^Apple (?:clang|LLVM) version) ([0-9]+\.[0-9]+)")

def get_gas_version(cc):
  try:
    custom_env = os.environ.copy()
    custom_env["LC_ALL"] = "C"
    proc = subprocess.Popen(shlex.split(cc) + ['-Wa,-v', '-c', '-o',
                                               '/dev/null', '-x',
                                               'assembler',  '/dev/null'],
                            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE, env=custom_env)
  except OSError:
    error('''No acceptable C compiler found!
       Please make sure you have a C compiler installed on your system and/or
       consider adjusting the CC environment variable if you installed
       it in a non-standard prefix.''')

  gas_ret = to_utf8(proc.communicate()[1])
  match = re.match(r"GNU assembler version ([2-9]\.[0-9]+)", gas_ret)

  if match:
    return match.group(1)
  else:
    warn('Could not recognize `gas`: ' + gas_ret)
    return '0.0'




def check_compiler(o,options):
  if sys.platform == 'win32':
    if not options.openssl_no_asm and options.dest_cpu in ('x86', 'x64'):
      nasm_version = get_nasm_version('nasm')
      o['variables']['nasm_version'] = nasm_version
      if nasm_version == '0.0':
        o['variables']['openssl_no_asm'] = 1
    return

  ok, is_clang, clang_version, gcc_version = try_check_compiler(CXX, 'c++')
  version_str = ".".join(map(str, clang_version if is_clang else gcc_version))
  print_verbose('Detected %sC++ compiler (CXX=%s) version: %s' %
                ('clang ' if is_clang else '', CXX, version_str),options)
  if not ok:
    warn('failed to autodetect C++ compiler version (CXX=%s)' % CXX)
  elif clang_version < (8, 0, 0) if is_clang else gcc_version < (6, 3, 0):
    warn('C++ compiler (CXX=%s, %s) too old, need g++ 6.3.0 or clang++ 8.0.0' %
         (CXX, version_str))

  ok, is_clang, clang_version, gcc_version = try_check_compiler(CC, 'c')
  version_str = ".".join(map(str, clang_version if is_clang else gcc_version))
  print_verbose('Detected %sC compiler (CC=%s) version: %s' %
                ('clang ' if is_clang else '', CC, version_str),options)
  if not ok:
    warn('failed to autodetect C compiler version (CC=%s)' % CC)
  elif not is_clang and gcc_version < (4, 2, 0):
    # clang 3.2 is a little white lie because any clang version will probably
    # do for the C bits.  However, we might as well encourage people to upgrade
    # to a version that is not completely ancient.
    warn('C compiler (CC=%s, %s) too old, need gcc 4.2 or clang 3.2' %
         (CC, version_str))

  o['variables']['llvm_version'] = get_llvm_version(CC) if is_clang else '0.0'

  # Need xcode_version or gas_version when openssl asm files are compiled.
  if options.without_ssl or options.openssl_no_asm or options.shared_openssl:
    return

  if is_clang:
    if sys.platform == 'darwin':
      o['variables']['xcode_version'] = get_xcode_version(CC)
  else:
    o['variables']['gas_version'] = get_gas_version(CC)


def cc_macros(cc=None):
  """Checks predefined macros using the C compiler command."""
  try:
    p = subprocess.Popen(shlex.split(cc or CC) + ['-dM', '-E', '-'],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
  except OSError:
    error('''No acceptable C compiler found!
       Please make sure you have a C compiler installed on your system and/or
       consider adjusting the CC environment variable if you installed
       it in a non-standard prefix.''')

  p.stdin.write(b'\n')
  out = to_utf8(p.communicate()[0]).split('\n')

  k = {}
  for line in out:
    lst = shlex.split(line)
    if len(lst) > 2:
      key = lst[1]
      val = lst[2]
      k[key] = val
  return k


def is_arch_armv7():
  """Check for ARMv7 instructions"""
  cc_macros_cache = cc_macros()
  return cc_macros_cache.get('__ARM_ARCH') == '7'



def is_arch_armv6():
  """Check for ARMv6 instructions"""
  cc_macros_cache = cc_macros()
  return cc_macros_cache.get('__ARM_ARCH') == '6'


def is_arm_hard_float_abi():
  """Check for hardfloat or softfloat eabi on ARM"""
  # GCC versions 4.6 and above define __ARM_PCS or __ARM_PCS_VFP to specify
  # the Floating Point ABI used (PCS stands for Procedure Call Standard).
  # We use these as well as a couple of other defines to statically determine
  # what FP ABI used.

  return '__ARM_PCS_VFP' in cc_macros()



def host_arch_cc():
  """Host architecture check using the CC command."""

  if sys.platform.startswith('aix'):
    # we only support gcc at this point and the default on AIX
    # would be xlc so hard code gcc
    k = cc_macros('gcc')
  else:
    k = cc_macros(os.environ.get('CC_host'))

  matchup = {
    '__aarch64__' : 'arm64',
    '__arm__'     : 'arm',
    '__i386__'    : 'ia32',
    '__MIPSEL__'  : 'mipsel',
    '__mips__'    : 'mips',
    '__PPC64__'   : 'ppc64',
    '__PPC__'     : 'ppc64',
    '__x86_64__'  : 'x64',
    '__s390x__'   : 's390x',
  }

  rtn = 'ia32' # default

  for i in matchup:
    if i in k and k[i] != '0':
      rtn = matchup[i]
      break

  if rtn == 'mipsel' and '_LP64' in k:
    rtn = 'mips64el'

  return rtn


def host_arch_win():
  """Host architecture check using environ vars (better way to do this?)"""

  observed_arch = os.environ.get('PROCESSOR_ARCHITECTURE', 'x86')
  arch = os.environ.get('PROCESSOR_ARCHITEW6432', observed_arch)

  matchup = {
    'AMD64'  : 'x64',
    'x86'    : 'ia32',
    'arm'    : 'arm',
    'mips'   : 'mips',
  }

  return matchup.get(arch, 'ia32')



def configure_arm(o,options):
  if options.arm_float_abi:
    arm_float_abi = options.arm_float_abi
  elif is_arm_hard_float_abi():
    arm_float_abi = 'hard'
  else:
    arm_float_abi = 'default'

  arm_fpu = 'vfp'

  if is_arch_armv7():
    arm_fpu = 'vfpv3'
    o['variables']['arm_version'] = '7'
  else:
    o['variables']['arm_version'] = '6' if is_arch_armv6() else 'default'

  o['variables']['arm_thumb'] = 0      # -marm
  o['variables']['arm_float_abi'] = arm_float_abi

  if options.dest_os == 'android':
    arm_fpu = 'vfpv3'
    o['variables']['arm_version'] = '7'

  o['variables']['arm_fpu'] = options.arm_fpu or arm_fpu


def configure_mips(o, target_arch,options):
  can_use_fpu_instructions = (options.mips_float_abi != 'soft')
  o['variables']['v8_can_use_fpu_instructions'] = b(can_use_fpu_instructions)
  o['variables']['v8_use_mips_abi_hardfloat'] = b(can_use_fpu_instructions)
  o['variables']['mips_arch_variant'] = options.mips_arch_variant
  o['variables']['mips_fpu_mode'] = options.mips_fpu_mode
  host_byteorder = 'little' if target_arch in ('mipsel', 'mips64el') else 'big'
  o['variables']['v8_host_byteorder'] = host_byteorder


def gcc_version_ge(version_checked):
  for compiler in [(CC, 'c'), (CXX, 'c++')]:
    ok, is_clang, clang_version, compiler_version = \
      try_check_compiler(compiler[0], compiler[1])
    if is_clang or compiler_version < version_checked:
      return False
  return True



def configure_node(o,options,flavor,node_version_h):
  if options.dest_os == 'android':
    o['variables']['OS'] = 'android'
  o['variables']['node_prefix'] = options.prefix
  o['variables']['node_install_npm'] = b(not options.without_npm)
  o['variables']['debug_node'] = b(options.debug_node)
  o['default_configuration'] = 'Debug' if options.debug else 'Release'
  o['variables']['error_on_warn'] = b(options.error_on_warn)

  host_arch = host_arch_win() if os.name == 'nt' else host_arch_cc()
  target_arch = options.dest_cpu or host_arch
  # ia32 is preferred by the build tools (GYP) over x86 even if we prefer the latter
  # the Makefile resets this to x86 afterward
  if target_arch == 'x86':
    target_arch = 'ia32'
  # x86_64 is common across linuxes, allow it as an alias for x64
  if target_arch == 'x86_64':
    target_arch = 'x64'
  o['variables']['host_arch'] = host_arch
  o['variables']['target_arch'] = target_arch
  o['variables']['node_byteorder'] = sys.byteorder

  cross_compiling = (options.cross_compiling
                     if options.cross_compiling is not None
                     else target_arch != host_arch)
  if cross_compiling:
    os.environ['GYP_CROSSCOMPILE'] = "1"
  if options.unused_without_snapshot:
    warn('building --without-snapshot is no longer possible')

  o['variables']['want_separate_host_toolset'] = int(cross_compiling)

  if options.without_node_snapshot or options.node_builtin_modules_path:
    o['variables']['node_use_node_snapshot'] = 'false'
  else:
    o['variables']['node_use_node_snapshot'] = b(
      not cross_compiling and not options.shared)

  if options.without_node_code_cache or options.node_builtin_modules_path:
    o['variables']['node_use_node_code_cache'] = 'false'
  else:
    # TODO(refack): fix this when implementing embedded code-cache when cross-compiling.
    o['variables']['node_use_node_code_cache'] = b(
      not cross_compiling and not options.shared)

  if target_arch == 'arm':
    configure_arm(o,options)
  elif target_arch in ('mips', 'mipsel', 'mips64el'):
    configure_mips(o, target_arch,options)

  if flavor == 'aix':
    o['variables']['node_target_type'] = 'static_library'

  if flavor != 'linux' and (options.enable_pgo_generate or options.enable_pgo_use):
    raise Exception(
      'The pgo option is supported only on linux.')

  if flavor == 'linux':
    if options.enable_pgo_generate or options.enable_pgo_use:
      version_checked = (5, 4, 1)
      if not gcc_version_ge(version_checked):
        version_checked_str = ".".join(map(str, version_checked))
        raise Exception(
          'The options --enable-pgo-generate and --enable-pgo-use '
          'are supported for gcc and gxx %s or newer only.' % (version_checked_str))

    if options.enable_pgo_generate and options.enable_pgo_use:
      raise Exception(
        'Only one of the --enable-pgo-generate or --enable-pgo-use options '
        'can be specified at a time. You would like to use '
        '--enable-pgo-generate first, profile node, and then recompile '
        'with --enable-pgo-use')

  o['variables']['enable_pgo_generate'] = b(options.enable_pgo_generate)
  o['variables']['enable_pgo_use']      = b(options.enable_pgo_use)

  if flavor != 'linux' and (options.enable_lto):
    raise Exception(
      'The lto option is supported only on linux.')

  if flavor == 'linux':
    if options.enable_lto:
      version_checked = (5, 4, 1)
      if not gcc_version_ge(version_checked):
        version_checked_str = ".".join(map(str, version_checked))
        raise Exception(
          'The option --enable-lto is supported for gcc and gxx %s'
          ' or newer only.' % (version_checked_str))

  o['variables']['enable_lto'] = b(options.enable_lto)

  if flavor in ('solaris', 'mac', 'linux', 'freebsd'):
    use_dtrace = not options.without_dtrace
    # Don't enable by default on linux and freebsd
    if flavor in ('linux', 'freebsd'):
      use_dtrace = options.with_dtrace

    if flavor == 'linux':
      if options.systemtap_includes:
        o['include_dirs'] += [options.systemtap_includes]
    o['variables']['node_use_dtrace'] = b(use_dtrace)
  elif options.with_dtrace:
    raise Exception(
       'DTrace is currently only supported on SunOS, MacOS or Linux systems.')
  else:
    o['variables']['node_use_dtrace'] = 'false'

  if options.node_use_large_pages or options.node_use_large_pages_script_lld:
    warn('''The `--use-largepages` and `--use-largepages-script-lld` options
         have no effect during build time. Support for mapping to large pages is
         now a runtime option of Node.js. Run `node --use-largepages` or add
         `--use-largepages` to the `NODE_OPTIONS` environment variable once
         Node.js is built to enable mapping to large pages.''')

  if options.no_ifaddrs:
    o['defines'] += ['SUNOS_NO_IFADDRS']

  # By default, enable ETW on Windows.
  if flavor == 'win':
    o['variables']['node_use_etw'] = b(not options.without_etw)
  elif options.with_etw:
    raise Exception('ETW is only supported on Windows.')
  else:
    o['variables']['node_use_etw'] = 'false'

  o['variables']['node_with_ltcg'] = b(options.with_ltcg)
  if flavor != 'win' and options.with_ltcg:
    raise Exception('Link Time Code Generation is only supported on Windows.')

  if options.tag:
    o['variables']['node_tag'] = '-' + options.tag
  else:
    o['variables']['node_tag'] = ''

  o['variables']['node_release_urlbase'] = options.release_urlbase or ''

  if options.v8_options:
    o['variables']['node_v8_options'] = options.v8_options.replace('"', '\\"')

  if options.enable_static:
    o['variables']['node_target_type'] = 'static_library'

  o['variables']['node_debug_lib'] = b(options.node_debug_lib)

  if options.debug_nghttp2:
    o['variables']['debug_nghttp2'] = 1
  else:
    o['variables']['debug_nghttp2'] = 'false'

  if options.experimental_quic:
    if options.shared_openssl:
      raise Exception('QUIC requires a modified version of OpenSSL and '
                      'cannot be enabled when using --shared-openssl.')
    o['variables']['experimental_quic'] = 1
  else:
    o['variables']['experimental_quic'] = 'false'

  o['variables']['node_no_browser_globals'] = b(options.no_browser_globals)

  o['variables']['node_shared'] = b(options.shared)
  node_module_version = getmoduleversion.get_version(node_version_h)

  if options.dest_os == 'android':
    shlib_suffix = 'so'
  elif sys.platform == 'darwin':
    shlib_suffix = '%s.dylib'
  elif sys.platform.startswith('aix'):
    shlib_suffix = '%s.a'
  else:
    shlib_suffix = 'so.%s'
  if '%s' in shlib_suffix:
    shlib_suffix %= node_module_version

  o['variables']['node_module_version'] = int(node_module_version)
  o['variables']['shlib_suffix'] = shlib_suffix

  if options.linked_module:
    o['variables']['library_files'] = options.linked_module

  o['variables']['asan'] = int(options.enable_asan or 0)

  if options.coverage:
    o['variables']['coverage'] = 'true'
  else:
    o['variables']['coverage'] = 'false'

  if options.shared:
    o['variables']['node_target_type'] = 'shared_library'
  elif options.enable_static:
    o['variables']['node_target_type'] = 'static_library'
  else:
    o['variables']['node_target_type'] = 'executable'

  if options.node_builtin_modules_path:
    print('Warning! Loading builtin modules from disk is for development')
    o['variables']['node_builtin_modules_path'] = options.node_builtin_modules_path




#####
def configure_napi(output,node_napi_h):
  version = getnapibuildversion.get_napi_version(node_napi_h)
  output['variables']['napi_build_version'] = version



def configure_library(options,lib, output, pkgname=None):
  shared_lib = 'shared_' + lib
  output['variables']['node_' + shared_lib] = b(getattr(options, shared_lib))

  if getattr(options, shared_lib):
    (pkg_libs, pkg_cflags, pkg_libpath, _) = pkg_config(pkgname or lib)

    if options.__dict__[shared_lib + '_includes']:
      output['include_dirs'] += [options.__dict__[shared_lib + '_includes']]
    elif pkg_cflags:
      stripped_flags = [flag.strip() for flag in pkg_cflags.split('-I')]
      output['include_dirs'] += [flag for flag in stripped_flags if flag]

    # libpath needs to be provided ahead libraries
    if options.__dict__[shared_lib + '_libpath']:
      if flavor == 'win':
        if 'msvs_settings' not in output:
          output['msvs_settings'] = { 'VCLinkerTool': { 'AdditionalOptions': [] } }
        output['msvs_settings']['VCLinkerTool']['AdditionalOptions'] += [
          '/LIBPATH:%s' % options.__dict__[shared_lib + '_libpath']]
      else:
        output['libraries'] += [
            '-L%s' % options.__dict__[shared_lib + '_libpath']]
    elif pkg_libpath:
      output['libraries'] += [pkg_libpath]

    default_libs = getattr(options, shared_lib + '_libname')
    default_libs = ['-l{0}'.format(l) for l in default_libs.split(',')]

    if default_libs:
      output['libraries'] += default_libs
    elif pkg_libs:
      output['libraries'] += pkg_libs.split()



def configure_v8(o,options):
  o['variables']['v8_enable_lite_mode'] = 1 if options.v8_lite_mode else 0
  o['variables']['v8_enable_gdbjit'] = 1 if options.gdb else 0
  o['variables']['v8_no_strict_aliasing'] = 1  # Work around compiler bugs.
  o['variables']['v8_optimized_debug'] = 0 if options.v8_non_optimized_debug else 1
  o['variables']['dcheck_always_on'] = 1 if options.v8_with_dchecks else 0
  o['variables']['v8_enable_object_print'] = 1 if options.v8_enable_object_print else 0
  o['variables']['v8_random_seed'] = 0  # Use a random seed for hash tables.
  o['variables']['v8_promise_internal_field_count'] = 1 # Add internal field to promises for async hooks.
  o['variables']['v8_use_siphash'] = 0 if options.without_siphash else 1
  o['variables']['v8_enable_pointer_compression'] = 1 if options.enable_pointer_compression else 0
  o['variables']['v8_enable_31bit_smis_on_64bit_arch'] = 1 if options.enable_pointer_compression else 0
  o['variables']['v8_trace_maps'] = 1 if options.trace_maps else 0
  o['variables']['node_use_v8_platform'] = b(not options.without_v8_platform)
  o['variables']['node_use_bundled_v8'] = b(not options.without_bundled_v8)
  o['variables']['force_dynamic_crt'] = 1 if options.shared else 0
  o['variables']['node_enable_d8'] = b(options.enable_d8)
  if options.enable_d8:
    o['variables']['test_isolation_mode'] = 'noop'  # Needed by d8.gyp.
  if options.without_bundled_v8 and options.enable_d8:
    raise Exception('--enable-d8 is incompatible with --without-bundled-v8.')


def configure_openssl(o,options):
  variables = o['variables']
  variables['node_use_openssl'] = b(not options.without_ssl)
  variables['node_shared_openssl'] = b(options.shared_openssl)
  variables['openssl_is_fips'] = b(options.openssl_is_fips)
  variables['openssl_fips'] = ''

  if options.openssl_no_asm:
    variables['openssl_no_asm'] = 1

  if options.without_ssl:
    def without_ssl_error(option):
      error('--without-ssl is incompatible with %s' % option)
    if options.shared_openssl:
      without_ssl_error('--shared-openssl')
    if options.openssl_no_asm:
      without_ssl_error('--openssl-no-asm')
    if options.openssl_fips:
      without_ssl_error('--openssl-fips')
    if options.openssl_default_cipher_list:
      without_ssl_error('--openssl-default-cipher-list')
    if options.experimental_quic:
      without_ssl_error('--experimental-quic')
    return

  if options.use_openssl_ca_store:
    o['defines'] += ['NODE_OPENSSL_CERT_STORE']
  if options.openssl_system_ca_path:
    variables['openssl_system_ca_path'] = options.openssl_system_ca_path
  variables['node_without_node_options'] = b(options.without_node_options)
  if options.without_node_options:
      o['defines'] += ['NODE_WITHOUT_NODE_OPTIONS']
  if options.openssl_default_cipher_list:
    variables['openssl_default_cipher_list'] = \
            options.openssl_default_cipher_list

  if not options.shared_openssl and not options.openssl_no_asm:
    is_x86 = 'x64' in variables['target_arch'] or 'ia32' in variables['target_arch']
    
    # blob/OpenSSL_1_1_0-stable/crypto/modes/asm/aesni-gcm-x86_64.pl#L52-L69
    openssl110_asm_supported = \
      ('gas_version' in variables and StrictVersion(variables['gas_version']) >= StrictVersion('2.23')) or \
      ('xcode_version' in variables and StrictVersion(variables['xcode_version']) >= StrictVersion('5.0')) or \
      ('llvm_version' in variables and StrictVersion(variables['llvm_version']) >= StrictVersion('3.3')) or \
      ('nasm_version' in variables and StrictVersion(variables['nasm_version']) >= StrictVersion('2.10'))

    if is_x86 and not openssl110_asm_supported:
      error('''Did not find a new enough assembler, install one or build with
       --openssl-no-asm.
       Please refer to BUILDING.md''')

  elif options.openssl_no_asm:
    warn('''--openssl-no-asm will result in binaries that do not take advantage
         of modern CPU cryptographic instructions and will therefore be slower.
         Please refer to BUILDING.md''')

  if options.openssl_no_asm and options.shared_openssl:
    error('--openssl-no-asm is incompatible with --shared-openssl')

  if options.openssl_fips or options.openssl_fips == '':
     error('FIPS is not supported in this version of Node.js')
  configure_library(options,'openssl', o)


def configure_static(o,options):
  if options.fully_static or options.partly_static:
    if flavor == 'mac':
      warn("Generation of static executable will not work on OSX "
            "when using the default compilation environment")
      return

    if options.fully_static:
      o['libraries'] += ['-static']
    elif options.partly_static:
      o['libraries'] += ['-static-libgcc', '-static-libstdc++']
      if options.enable_asan:
        o['libraries'] += ['-static-libasan']



def write(filename, data,options):
  print_verbose('creating %s' % filename,options)
  with open(filename, 'w+') as f:
    f.write(data)


def glob_to_var(dir_base, dir_sub, patch_dir):
  list = []
  dir_all = '%s/%s' % (dir_base, dir_sub)
  files = os.walk(dir_all)
  for ent in files:
    (path, dirs, files) = ent
    for file in files:
      if file.endswith('.cpp') or file.endswith('.c') or file.endswith('.h'):
        # srcfile uses "slash" as dir separator as its output is consumed by gyp
        srcfile = '%s/%s' % (dir_sub, file)
        if patch_dir:
          patchfile = '%s/%s/%s' % (dir_base, patch_dir, file)
          if os.path.isfile(patchfile):
            srcfile = '%s/%s' % (patch_dir, file)
            info('Using floating patch "%s" from "%s"' % (patchfile, dir_base))
        list.append(srcfile)
    break
  return list


do_not_edit = '# Do not edit. Generated by the configure script.\n'


def configure_intl(o,options,icu_versions,icu_current_ver_dep):
  auto_downloads = nodedownload.parse(options.download_list)
  def icu_download(path):
    depFile = icu_current_ver_dep
    with open(depFile) as f:
      icus = json.load(f)
    # download ICU, if needed
    if not os.access(options.download_path, os.W_OK):
      error('''Cannot write to desired download path.
        Either create it or verify permissions.''')
    attemptdownload = nodedownload.candownload(auto_downloads, "icu")
    for icu in icus:
      url = icu['url']
      (expectHash, hashAlgo, allAlgos) = nodedownload.findHash(icu)
      if not expectHash:
        error('''Could not find a hash to verify ICU download.
          %s may be incorrect.
          For the entry %s,
          Expected one of these keys: %s''' % (depFile, url, ' '.join(allAlgos)))
      local = url.split('/')[-1]
      targetfile = os.path.join(options.download_path, local)
      if not os.path.isfile(targetfile):
        if attemptdownload:
          nodedownload.retrievefile(url, targetfile)
      else:
        print('Re-using existing %s' % targetfile)
      if os.path.isfile(targetfile):
        print('Checking file integrity with %s:\r' % hashAlgo)
        gotHash = nodedownload.checkHash(targetfile, hashAlgo)
        print('%s:      %s  %s' % (hashAlgo, gotHash, targetfile))
        if (expectHash == gotHash):
          return targetfile
        else:
          warn('Expected: %s      *MISMATCH*' % expectHash)
          warn('\n ** Corrupted ZIP? Delete %s to retry download.\n' % targetfile)
    return None
  icu_config = {
    'variables': {}
  }
  icu_config_name = 'icu_config.gypi'

  # write an empty file to start with
  write(icu_config_name, do_not_edit +pprint.pformat(icu_config, indent=2) + '\n',options)

  # always set icu_small, node.gyp depends on it being defined.
  o['variables']['icu_small'] = b(False)

  with_intl = options.with_intl
  with_icu_source = options.with_icu_source
  have_icu_path = bool(options.with_icu_path)
  if have_icu_path and with_intl != 'none':
    error('Cannot specify both --with-icu-path and --with-intl')
  elif have_icu_path:
    # Chromium .gyp mode: --with-icu-path
    o['variables']['v8_enable_i18n_support'] = 1
    # use the .gyp given
    o['variables']['icu_gyp_path'] = options.with_icu_path
    return
  # --with-intl=<with_intl>
  # set the default
  if with_intl in (None, 'none'):
    o['variables']['v8_enable_i18n_support'] = 0
    return  # no Intl
  elif with_intl == 'small-icu':
    # small ICU (English only)
    o['variables']['v8_enable_i18n_support'] = 1
    o['variables']['icu_small'] = b(True)
    locs = set(options.with_icu_locales.split(','))
    locs.add('root')  # must have root
    o['variables']['icu_locales'] = ','.join(str(loc) for loc in locs)
    # We will check a bit later if we can use the canned deps/icu-small
    o['variables']['icu_default_data'] = options.with_icu_default_data_dir or ''
  elif with_intl == 'full-icu':
    # full ICU
    o['variables']['v8_enable_i18n_support'] = 1
  elif with_intl == 'system-icu':
    # ICU from pkg-config.
    o['variables']['v8_enable_i18n_support'] = 1
    pkgicu = pkg_config('icu-i18n')
    if not pkgicu[0]:
      error('''Could not load pkg-config data for "icu-i18n".
       See above errors or the README.md.''')
    (libs, cflags, libpath, icuversion) = pkgicu
    icu_ver_major = icuversion.split('.')[0]
    o['variables']['icu_ver_major'] = icu_ver_major
    if int(icu_ver_major) < icu_versions['minimum_icu']:
      error('icu4c v%s is too old, v%d.x or later is required.' %
            (icuversion, icu_versions['minimum_icu']))
    # libpath provides linker path which may contain spaces
    if libpath:
      o['libraries'] += [libpath]
    # safe to split, cannot contain spaces
    o['libraries'] += libs.split()
    if cflags:
      stripped_flags = [flag.strip() for flag in cflags.split('-I')]
      o['include_dirs'] += [flag for flag in stripped_flags if flag]
    # use the "system" .gyp
    o['variables']['icu_gyp_path'] = 'tools/icu/icu-system.gyp'
    return

  # this is just the 'deps' dir. Used for unpacking.
  icu_parent_path = 'deps'

  # The full path to the ICU source directory. Should not include './'.
  icu_deps_path = 'deps/icu'
  icu_full_path = icu_deps_path

  # icu-tmp is used to download and unpack the ICU tarball.
  icu_tmp_path = os.path.join(icu_parent_path, 'icu-tmp')

  # canned ICU. see tools/icu/README.md to update.
  canned_icu_dir = 'deps/icu-small'

  # use the README to verify what the canned ICU is
  canned_is_full = os.path.isfile(os.path.join(canned_icu_dir, 'README-FULL-ICU.txt'))
  canned_is_small = os.path.isfile(os.path.join(canned_icu_dir, 'README-SMALL-ICU.txt'))
  if canned_is_small:
    warn('Ignoring %s - in-repo small icu is no longer supported.' % canned_icu_dir)

  # We can use 'deps/icu-small' - pre-canned ICU *iff*
  # - canned_is_full AND
  # - with_icu_source is unset (i.e. no other ICU was specified)
  #
  # This is *roughly* equivalent to
  # $ configure --with-intl=full-icu --with-icu-source=deps/icu-small
  # .. Except that we avoid copying icu-small over to deps/icu.
  # In this default case, deps/icu is ignored, although make clean will
  # still harmlessly remove deps/icu.

  if (not with_icu_source) and canned_is_full:
    # OK- we can use the canned ICU.
    icu_full_path = canned_icu_dir
    icu_config['variables']['icu_full_canned'] = 1
  # --with-icu-source processing
  # now, check that they didn't pass --with-icu-source=deps/icu
  elif with_icu_source and os.path.abspath(icu_full_path) == os.path.abspath(with_icu_source):
    warn('Ignoring redundant --with-icu-source=%s' % with_icu_source)
    with_icu_source = None
  # if with_icu_source is still set, try to use it.
  if with_icu_source:
    if os.path.isdir(icu_full_path):
      print('Deleting old ICU source: %s' % icu_full_path)
      shutil.rmtree(icu_full_path)
    # now, what path was given?
    if os.path.isdir(with_icu_source):
      # it's a path. Copy it.
      print('%s -> %s' % (with_icu_source, icu_full_path))
      shutil.copytree(with_icu_source, icu_full_path)
    else:
      # could be file or URL.
      # Set up temporary area
      if os.path.isdir(icu_tmp_path):
        shutil.rmtree(icu_tmp_path)
      os.mkdir(icu_tmp_path)
      icu_tarball = None
      if os.path.isfile(with_icu_source):
        # it's a file. Try to unpack it.
        icu_tarball = with_icu_source
      else:
        # Can we download it?
        local = os.path.join(icu_tmp_path, with_icu_source.split('/')[-1])  # local part
        icu_tarball = nodedownload.retrievefile(with_icu_source, local)
      # continue with "icu_tarball"
      nodedownload.unpack(icu_tarball, icu_tmp_path)
      # Did it unpack correctly? Should contain 'icu'
      tmp_icu = os.path.join(icu_tmp_path, 'icu')
      if os.path.isdir(tmp_icu):
        os.rename(tmp_icu, icu_full_path)
        shutil.rmtree(icu_tmp_path)
      else:
        shutil.rmtree(icu_tmp_path)
        error('--with-icu-source=%s did not result in an "icu" dir.' % \
               with_icu_source)

  # ICU mode. (icu-generic.gyp)
  o['variables']['icu_gyp_path'] = 'tools/icu/icu-generic.gyp'
  # ICU source dir relative to tools/icu (for .gyp file)
  o['variables']['icu_path'] = icu_full_path
  if not os.path.isdir(icu_full_path):
    # can we download (or find) a zipfile?
    localzip = icu_download(icu_full_path)
    if localzip:
      nodedownload.unpack(localzip, icu_parent_path)
    else:
      warn('* ECMA-402 (Intl) support didn\'t find ICU in %s..' % icu_full_path)
  if not os.path.isdir(icu_full_path):
    error('''Cannot build Intl without ICU in %s.
       Fix, or disable with "--with-intl=none"''' % icu_full_path)
  else:
    print_verbose('* Using ICU in %s' % icu_full_path,options)
  # Now, what version of ICU is it? We just need the "major", such as 54.
  # uvernum.h contains it as a #define.
  uvernum_h = os.path.join(icu_full_path, 'source/common/unicode/uvernum.h')
  if not os.path.isfile(uvernum_h):
    error('Could not load %s - is ICU installed?' % uvernum_h)
  icu_ver_major = None
  matchVerExp = r'^\s*#define\s+U_ICU_VERSION_SHORT\s+"([^"]*)".*'
  match_version = re.compile(matchVerExp)
  with io.open(uvernum_h, encoding='utf8') as in_file:
    for line in in_file:
      m = match_version.match(line)
      if m:
        icu_ver_major = str(m.group(1))
  if not icu_ver_major:
    error('Could not read U_ICU_VERSION_SHORT version from %s' % uvernum_h)
  elif int(icu_ver_major) < icu_versions['minimum_icu']:
    error('icu4c v%s.x is too old, v%d.x or later is required.' %
          (icu_ver_major, icu_versions['minimum_icu']))
  icu_endianness = sys.byteorder[0]
  o['variables']['icu_ver_major'] = icu_ver_major
  o['variables']['icu_endianness'] = icu_endianness
  icu_data_file_l = 'icudt%s%s.dat' % (icu_ver_major, 'l') # LE filename
  icu_data_file = 'icudt%s%s.dat' % (icu_ver_major, icu_endianness)
  # relative to configure
  icu_data_path = os.path.join(icu_full_path,
                               'source/data/in',
                               icu_data_file_l) # LE
  compressed_data = '%s.bz2' % (icu_data_path)
  if not os.path.isfile(icu_data_path) and os.path.isfile(compressed_data):
    # unpack. deps/icu is a temporary path
    if os.path.isdir(icu_tmp_path):
      shutil.rmtree(icu_tmp_path)
    os.mkdir(icu_tmp_path)
    icu_data_path = os.path.join(icu_tmp_path, icu_data_file_l)
    with open(icu_data_path, 'wb') as outf:
        inf = bz2.BZ2File(compressed_data, 'rb')
        try:
          shutil.copyfileobj(inf, outf)
        finally:
          inf.close()
    # Now, proceed..

  # relative to dep..
  icu_data_in = os.path.join('..','..', icu_data_path)
  if not os.path.isfile(icu_data_path) and icu_endianness != 'l':
    # use host endianness
    icu_data_path = os.path.join(icu_full_path,
                                 'source/data/in',
                                 icu_data_file) # will be generated
  if not os.path.isfile(icu_data_path):
    # .. and we're not about to build it from .gyp!
    error('''ICU prebuilt data file %s does not exist.
       See the README.md.''' % icu_data_path)

  # this is the input '.dat' file to use .. icudt*.dat
  # may be little-endian if from a icu-project.org tarball
  o['variables']['icu_data_in'] = icu_data_in

  # map from variable name to subdirs
  icu_src = {
    'stubdata': 'stubdata',
    'common': 'common',
    'i18n': 'i18n',
    'tools': 'tools/toolutil',
    'genccode': 'tools/genccode',
    'genrb': 'tools/genrb',
    'icupkg': 'tools/icupkg',
  }
  # this creates a variable icu_src_XXX for each of the subdirs
  # with a list of the src files to use
  for i in icu_src:
    var  = 'icu_src_%s' % i
    path = '../../%s/source/%s' % (icu_full_path, icu_src[i])
    icu_config['variables'][var] = glob_to_var('tools/icu', path, 'patches/%s/source/%s' % (icu_ver_major, icu_src[i]) )
  # calculate platform-specific genccode args
  # print("platform %s, flavor %s" % (sys.platform, flavor))
  # if sys.platform == 'darwin':
  #   shlib_suffix = '%s.dylib'
  # elif sys.platform.startswith('aix'):
  #   shlib_suffix = '%s.a'
  # else:
  #   shlib_suffix = 'so.%s'
  if flavor == 'win':
    icu_config['variables']['icu_asm_ext'] = 'obj'
    icu_config['variables']['icu_asm_opts'] = [ '-o ' ]
  elif with_intl == 'small-icu' or options.cross_compiling:
    icu_config['variables']['icu_asm_ext'] = 'c'
    icu_config['variables']['icu_asm_opts'] = []
  elif flavor == 'mac':
    icu_config['variables']['icu_asm_ext'] = 'S'
    icu_config['variables']['icu_asm_opts'] = [ '-a', 'gcc-darwin' ]
  elif sys.platform.startswith('aix'):
    icu_config['variables']['icu_asm_ext'] = 'S'
    icu_config['variables']['icu_asm_opts'] = [ '-a', 'xlc' ]
  else:
    # assume GCC-compatible asm is OK
    icu_config['variables']['icu_asm_ext'] = 'S'
    icu_config['variables']['icu_asm_opts'] = [ '-a', 'gcc' ]

  # write updated icu_config.gypi with a bunch of paths
  write(icu_config_name, do_not_edit +
        pprint.pformat(icu_config, indent=2) + '\n',options)
  return  # end of configure_intl



def configure_inspector(o,options):
  disable_inspector = (options.without_inspector or
                       options.with_intl in (None, 'none') or
                       options.without_ssl)
  o['variables']['v8_enable_inspector'] = 0 if disable_inspector else 1


def configure_section_file(o,options):
  try:
    proc = subprocess.Popen(['ld.gold'] + ['-v'], stdin = subprocess.PIPE,
                            stdout = subprocess.PIPE, stderr = subprocess.PIPE)
  except OSError:
    if options.node_section_ordering_info != "":
      warn('''No acceptable ld.gold linker found!''')
    return 0

  match = re.match(r"^GNU gold.*([0-9]+)\.([0-9]+)$",
                   proc.communicate()[0].decode("utf-8"))

  if match:
    gold_major_version = match.group(1)
    gold_minor_version = match.group(2)
    if int(gold_major_version) == 1 and int(gold_minor_version) <= 1:
      error('''GNU gold version must be greater than 1.2 in order to use section
            reordering''')

  if options.node_section_ordering_info != "":
    o['variables']['node_section_ordering_info'] = os.path.realpath(
      str(options.node_section_ordering_info))
  else:
    o['variables']['node_section_ordering_info'] = ""


def make_bin_override():
  if sys.platform == 'win32':
    raise Exception('make_bin_override should not be called on win32.')
  # If the system python is not the python we are running (which should be
  # python 2), then create a directory with a symlink called `python` to our
  # sys.executable. This directory will be prefixed to the PATH, so that
  # other tools that shell out to `python` will use the appropriate python

  which_python = which('python')
  if (which_python and
      os.path.realpath(which_python) == os.path.realpath(sys.executable)):
    return

  bin_override = os.path.abspath('out/tools/bin')
  try:
    os.makedirs(bin_override)
  except OSError as e:
    if e.errno != errno.EEXIST: raise e

  python_link = os.path.join(bin_override, 'python')
  try:
    os.unlink(python_link)
  except OSError as e:
    if e.errno != errno.ENOENT: raise e
  os.symlink(sys.executable, python_link)

  # We need to set the environment right now so that when gyp (in run_gyp)
  # shells out, it finds the right python (specifically at
  # https://github.com/nodejs/node/blob/d82e107/deps/v8/gypfiles/toolchain.gypi#L43)
  os.environ['PATH'] = bin_override + ':' + os.environ['PATH']
  return bin_override




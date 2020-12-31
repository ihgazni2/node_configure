import argparse
import nodedownload

def creat_parser(icu_versions):
    parser = argparse.ArgumentParser()
    valid_os = ('win', 'mac', 'solaris', 'freebsd', 'openbsd', 'linux','android', 'aix', 'cloudabi')
    valid_arch = ('arm', 'arm64', 'ia32', 'mips', 'mipsel', 'mips64el', 'ppc','ppc64', 'x32','x64', 'x86', 'x86_64', 's390x')
    valid_arm_float_abi = ('soft', 'softfp', 'hard')
    valid_arm_fpu = ('vfp', 'vfpv3', 'vfpv3-d16', 'neon')
    valid_mips_arch = ('loongson', 'r1', 'r2', 'r6', 'rx')
    valid_mips_fpu = ('fp32', 'fp64', 'fpxx')
    valid_mips_float_abi = ('soft', 'hard')
    valid_intl_modes = ('none', 'small-icu', 'full-icu', 'system-icu')
    # create option groups
    shared_optgroup = parser.add_argument_group(
        "Shared libraries",
        "Flags that allows you to control whether you want to build against "
        "built-in dependencies or its shared representations. If necessary, "
        "provide multiple libraries with comma."
    )
    intl_optgroup = parser.add_argument_group(
        "Internationalization",
        "Flags that lets you enable i18n features in Node.js as well as which "
        "library you want to build against."
    )
    http2_optgroup = parser.add_argument_group(
        "HTTP2",
        "Flags that allows you to control HTTP2 features in Node.js"
    )
    # Options should be in alphabetical order but keep --prefix at the top,
    # that's arguably the one people will be looking for most.
    parser.add_argument('--prefix',
        action='store',
        dest='prefix',
        default='/usr/local',
        help='select the install prefix [default: %(default)s]')
    parser.add_argument('--coverage',
        action='store_true',
        dest='coverage',
        default=None,
        help='Build node with code coverage enabled')
    parser.add_argument('--debug',
        action='store_true',
        dest='debug',
        default=None,
        help='also build debug build')
    parser.add_argument('--debug-node',
        action='store_true',
        dest='debug_node',
        default=None,
        help='build the Node.js part of the binary with debugging symbols')
    parser.add_argument('--dest-cpu',
        action='store',
        dest='dest_cpu',
        choices=valid_arch,
        help='CPU architecture to build for ({0})'.format(', '.join(valid_arch)))
    parser.add_argument('--cross-compiling',
        action='store_true',
        dest='cross_compiling',
        default=None,
        help='force build to be considered as cross compiled')
    parser.add_argument('--no-cross-compiling',
        action='store_false',
        dest='cross_compiling',
        default=None,
        help='force build to be considered as NOT cross compiled')
    parser.add_argument('--dest-os',
        action='store',
        dest='dest_os',
        choices=valid_os,
        help='operating system to build for ({0})'.format(', '.join(valid_os)))
    parser.add_argument('--error-on-warn',
        action='store_true',
        dest='error_on_warn',
        default=None,
        help='Turn compiler warnings into errors for node core sources.')
    parser.add_argument('--experimental-quic',
        action='store_true',
        dest='experimental_quic',
        default=None,
        help='enable experimental quic support')
    parser.add_argument('--gdb',
        action='store_true',
        dest='gdb',
        default=None,
        help='add gdb support')
    parser.add_argument('--no-ifaddrs',
        action='store_true',
        dest='no_ifaddrs',
        default=None,
        help='use on deprecated SunOS systems that do not support ifaddrs.h')
    parser.add_argument("--fully-static",
        action="store_true",
        dest="fully_static",
        default=None,
        help="Generate an executable without external dynamic libraries. This "
             "will not work on OSX when using the default compilation environment")
    parser.add_argument("--partly-static",
        action="store_true",
        dest="partly_static",
        default=None,
        help="Generate an executable with libgcc and libstdc++ libraries. This "
             "will not work on OSX when using the default compilation environment")
    parser.add_argument("--enable-pgo-generate",
        action="store_true",
        dest="enable_pgo_generate",
        default=None,
        help="Enable profiling with pgo of a binary. This feature is only available "
             "on linux with gcc and g++ 5.4.1 or newer.")
    parser.add_argument("--enable-pgo-use",
        action="store_true",
        dest="enable_pgo_use",
        default=None,
        help="Enable use of the profile generated with --enable-pgo-generate. This "
             "feature is only available on linux with gcc and g++ 5.4.1 or newer.")
    parser.add_argument("--enable-lto",
        action="store_true",
        dest="enable_lto",
        default=None,
        help="Enable compiling with lto of a binary. This feature is only available "
             "on linux with gcc and g++ 5.4.1 or newer.")
    parser.add_argument("--link-module",
        action="append",
        dest="linked_module",
        help="Path to a JS file to be bundled in the binary as a builtin. "
             "This module will be referenced by path without extension; "
             "e.g. /root/x/y.js will be referenced via require('root/x/y'). "
             "Can be used multiple times")
    parser.add_argument('--openssl-default-cipher-list',
        action='store',
        dest='openssl_default_cipher_list',
        help='Use the specified cipher list as the default cipher list')
    parser.add_argument("--openssl-no-asm",
        action="store_true",
        dest="openssl_no_asm",
        default=None,
        help="Do not build optimized assembly for OpenSSL")
    parser.add_argument('--openssl-fips',
        action='store',
        dest='openssl_fips',
        help='Build OpenSSL using FIPS canister .o file in supplied folder')
    parser.add_argument('--openssl-is-fips',
        action='store_true',
        dest='openssl_is_fips',
        default=None,
        help='specifies that the OpenSSL library is FIPS compatible')
    parser.add_argument('--openssl-use-def-ca-store',
        action='store_true',
        dest='use_openssl_ca_store',
        default=None,
        help='Use OpenSSL supplied CA store instead of compiled-in Mozilla CA copy.')
    parser.add_argument('--openssl-system-ca-path',
        action='store',
        dest='openssl_system_ca_path',
        help='Use the specified path to system CA (PEM format) in addition to '
             'the OpenSSL supplied CA store or compiled-in Mozilla CA copy.')
    parser.add_argument('--experimental-http-parser',
        action='store_true',
        dest='experimental_http_parser',
        default=None,
        help='(no-op)')
    shared_optgroup.add_argument('--shared-http-parser',
        action='store_true',
        dest='shared_http_parser',
        default=None,
        help='link to a shared http_parser DLL instead of static linking')
    shared_optgroup.add_argument('--shared-http-parser-includes',
        action='store',
        dest='shared_http_parser_includes',
        help='directory containing http_parser header files')
    shared_optgroup.add_argument('--shared-http-parser-libname',
        action='store',
        dest='shared_http_parser_libname',
        default='http_parser',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-http-parser-libpath',
        action='store',
        dest='shared_http_parser_libpath',
        help='a directory to search for the shared http_parser DLL')
    shared_optgroup.add_argument('--shared-libuv',
        action='store_true',
        dest='shared_libuv',
        default=None,
        help='link to a shared libuv DLL instead of static linking')
    shared_optgroup.add_argument('--shared-libuv-includes',
        action='store',
        dest='shared_libuv_includes',
        help='directory containing libuv header files')
    shared_optgroup.add_argument('--shared-libuv-libname',
        action='store',
        dest='shared_libuv_libname',
        default='uv',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-libuv-libpath',
        action='store',
        dest='shared_libuv_libpath',
        help='a directory to search for the shared libuv DLL')
    shared_optgroup.add_argument('--shared-nghttp2',
        action='store_true',
        dest='shared_nghttp2',
        default=None,
        help='link to a shared nghttp2 DLL instead of static linking')
    shared_optgroup.add_argument('--shared-nghttp2-includes',
        action='store',
        dest='shared_nghttp2_includes',
        help='directory containing nghttp2 header files')
    shared_optgroup.add_argument('--shared-nghttp2-libname',
        action='store',
        dest='shared_nghttp2_libname',
        default='nghttp2',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-nghttp2-libpath',
        action='store',
        dest='shared_nghttp2_libpath',
        help='a directory to search for the shared nghttp2 DLLs')
    shared_optgroup.add_argument('--shared-ngtcp2',
        action='store_true',
        dest='shared_ngtcp2',
        default=None,
        help='link to a shared ngtcp2 DLL instead of static linking')
    shared_optgroup.add_argument('--shared-ngtcp2-includes',
        action='store',
        dest='shared_ngtcp2_includes',
        help='directory containing ngtcp2 header files')
    shared_optgroup.add_argument('--shared-ngtcp2-libname',
        action='store',
        dest='shared_ngtcp2_libname',
        default='ngtcp2',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-ngtcp2-libpath',
        action='store',
        dest='shared_ngtcp2_libpath',
        help='a directory to search for the shared ngtcp2 DLLs')
    shared_optgroup.add_argument('--shared-nghttp3',
        action='store_true',
        dest='shared_nghttp3',
        default=None,
        help='link to a shared nghttp3 DLL instead of static linking')
    shared_optgroup.add_argument('--shared-nghttp3-includes',
        action='store',
        dest='shared_nghttp3_includes',
        help='directory containing nghttp3 header files')
    shared_optgroup.add_argument('--shared-nghttp3-libname',
        action='store',
        dest='shared_nghttp3_libname',
        default='nghttp3',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-nghttp3-libpath',
        action='store',
        dest='shared_nghttp3_libpath',
        help='a directory to search for the shared nghttp3 DLLs')
    shared_optgroup.add_argument('--shared-openssl',
        action='store_true',
        dest='shared_openssl',
        default=None,
        help='link to a shared OpenSSl DLL instead of static linking')
    shared_optgroup.add_argument('--shared-openssl-includes',
        action='store',
        dest='shared_openssl_includes',
        help='directory containing OpenSSL header files')
    shared_optgroup.add_argument('--shared-openssl-libname',
        action='store',
        dest='shared_openssl_libname',
        default='crypto,ssl',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-openssl-libpath',
        action='store',
        dest='shared_openssl_libpath',
        help='a directory to search for the shared OpenSSL DLLs')
    shared_optgroup.add_argument('--shared-zlib',
        action='store_true',
        dest='shared_zlib',
        default=None,
        help='link to a shared zlib DLL instead of static linking')
    shared_optgroup.add_argument('--shared-zlib-includes',
        action='store',
        dest='shared_zlib_includes',
        help='directory containing zlib header files')
    shared_optgroup.add_argument('--shared-zlib-libname',
        action='store',
        dest='shared_zlib_libname',
        default='z',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-zlib-libpath',
        action='store',
        dest='shared_zlib_libpath',
        help='a directory to search for the shared zlib DLL')
    shared_optgroup.add_argument('--shared-brotli',
        action='store_true',
        dest='shared_brotli',
        default=None,
        help='link to a shared brotli DLL instead of static linking')
    shared_optgroup.add_argument('--shared-brotli-includes',
        action='store',
        dest='shared_brotli_includes',
        help='directory containing brotli header files')
    shared_optgroup.add_argument('--shared-brotli-libname',
        action='store',
        dest='shared_brotli_libname',
        default='brotlidec,brotlienc',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-brotli-libpath',
        action='store',
        dest='shared_brotli_libpath',
        help='a directory to search for the shared brotli DLL')
    shared_optgroup.add_argument('--shared-cares',
        action='store_true',
        dest='shared_cares',
        default=None,
        help='link to a shared cares DLL instead of static linking')
    shared_optgroup.add_argument('--shared-cares-includes',
        action='store',
        dest='shared_cares_includes',
        help='directory containing cares header files')
    shared_optgroup.add_argument('--shared-cares-libname',
        action='store',
        dest='shared_cares_libname',
        default='cares',
        help='alternative lib name to link to [default: %(default)s]')
    shared_optgroup.add_argument('--shared-cares-libpath',
        action='store',
        dest='shared_cares_libpath',
        help='a directory to search for the shared cares DLL')
    parser.add_argument_group(shared_optgroup)
    parser.add_argument('--systemtap-includes',
        action='store',
        dest='systemtap_includes',
        help='directory containing systemtap header files')
    parser.add_argument('--tag',
        action='store',
        dest='tag',
        help='custom build tag')
    parser.add_argument('--release-urlbase',
        action='store',
        dest='release_urlbase',
        help='Provide a custom URL prefix for the `process.release` properties '
             '`sourceUrl` and `headersUrl`. When compiling a release build, this '
             'will default to https://nodejs.org/download/release/')
    parser.add_argument('--enable-d8',
        action='store_true',
        dest='enable_d8',
        default=None,
        help=argparse.SUPPRESS)  # Unsupported, undocumented.
    parser.add_argument('--enable-trace-maps',
        action='store_true',
        dest='trace_maps',
        default=None,
        help='Enable the --trace-maps flag in V8 (use at your own risk)')
    parser.add_argument('--experimental-enable-pointer-compression',
        action='store_true',
        dest='enable_pointer_compression',
        default=None,
        help='[Experimental] Enable V8 pointer compression (limits max heap to 4GB and breaks ABI compatibility)')
    parser.add_argument('--v8-options',
        action='store',
        dest='v8_options',
        help='v8 options to pass, see `node --v8-options` for examples.')
    parser.add_argument('--with-ossfuzz',
        action='store_true',
        dest='ossfuzz',
        default=None,
        help='Enables building of fuzzers. This command should be run in an OSS-Fuzz Docker image.')
    parser.add_argument('--with-arm-float-abi',
        action='store',
        dest='arm_float_abi',
        choices=valid_arm_float_abi,
        help='specifies which floating-point ABI to use ({0}).'.format(
            ', '.join(valid_arm_float_abi)))
    parser.add_argument('--with-arm-fpu',
        action='store',
        dest='arm_fpu',
        choices=valid_arm_fpu,
        help='ARM FPU mode ({0}) [default: %(default)s]'.format(
            ', '.join(valid_arm_fpu)))
    parser.add_argument('--with-mips-arch-variant',
        action='store',
        dest='mips_arch_variant',
        default='r2',
        choices=valid_mips_arch,
        help='MIPS arch variant ({0}) [default: %(default)s]'.format(
            ', '.join(valid_mips_arch)))
    parser.add_argument('--with-mips-fpu-mode',
        action='store',
        dest='mips_fpu_mode',
        default='fp32',
        choices=valid_mips_fpu,
        help='MIPS FPU mode ({0}) [default: %(default)s]'.format(
            ', '.join(valid_mips_fpu)))
    parser.add_argument('--with-mips-float-abi',
        action='store',
        dest='mips_float_abi',
        default='hard',
        choices=valid_mips_float_abi,
        help='MIPS floating-point ABI ({0}) [default: %(default)s]'.format(
            ', '.join(valid_mips_float_abi)))
    parser.add_argument('--with-dtrace',
        action='store_true',
        dest='with_dtrace',
        default=None,
        help='build with DTrace (default is true on sunos and darwin)')
    parser.add_argument('--with-etw',
        action='store_true',
        dest='with_etw',
        default=None,
        help='build with ETW (default is true on Windows)')
    parser.add_argument('--use-largepages',
        action='store_true',
        dest='node_use_large_pages',
        default=None,
        help='This option has no effect. --use-largepages is now a runtime option.')
    parser.add_argument('--use-largepages-script-lld',
        action='store_true',
        dest='node_use_large_pages_script_lld',
        default=None,
        help='This option has no effect. --use-largepages is now a runtime option.')
    parser.add_argument('--use-section-ordering-file',
        action='store',
        dest='node_section_ordering_info',
        default='',
        help='Pass a section ordering file to the linker. This requires that ' +
             'Node.js be linked using the gold linker. The gold linker must have ' +
             'version 1.2 or greater.')
    intl_optgroup.add_argument('--with-intl',
        action='store',
        dest='with_intl',
        default='full-icu',
        choices=valid_intl_modes,
        help='Intl mode (valid choices: {0}) [default: %(default)s]'.format(
            ', '.join(valid_intl_modes)))
    intl_optgroup.add_argument('--without-intl',
        action='store_const',
        dest='with_intl',
        const='none',
        help='Disable Intl, same as --with-intl=none (disables inspector)')
    intl_optgroup.add_argument('--with-icu-path',
        action='store',
        dest='with_icu_path',
        help='Path to icu.gyp (ICU i18n, Chromium version only.)')
    icu_default_locales='root,en'
    intl_optgroup.add_argument('--with-icu-locales',
        action='store',
        dest='with_icu_locales',
        default=icu_default_locales,
        help='Comma-separated list of locales for "small-icu". "root" is assumed. '
            '[default: %(default)s]')
    intl_optgroup.add_argument('--with-icu-source',
        action='store',
        dest='with_icu_source',
        help='Intl mode: optional local path to icu/ dir, or path/URL of '
            'the icu4c source archive. '
            'v%d.x or later recommended.' % icu_versions['minimum_icu'])
    intl_optgroup.add_argument('--with-icu-default-data-dir',
        action='store',
        dest='with_icu_default_data_dir',
        help='Path to the icuXXdt{lb}.dat file. If unspecified, ICU data will '
             'only be read if the NODE_ICU_DATA environment variable or the '
             '--icu-data-dir runtime argument is used. This option has effect '
             'only when Node.js is built with --with-intl=small-icu.')
    parser.add_argument('--with-ltcg',
        action='store_true',
        dest='with_ltcg',
        default=None,
        help='Use Link Time Code Generation. This feature is only available on Windows.')
    parser.add_argument('--without-node-snapshot',
        action='store_true',
        dest='without_node_snapshot',
        default=None,
        help='Turn off V8 snapshot integration. Currently experimental.')
    parser.add_argument('--without-node-code-cache',
        action='store_true',
        dest='without_node_code_cache',
        default=None,
        help='Turn off V8 Code cache integration.')
    intl_optgroup.add_argument('--download',
        action='store',
        dest='download_list',
        help=nodedownload.help())
    intl_optgroup.add_argument('--download-path',
        action='store',
        dest='download_path',
        default='deps',
        help='Download directory [default: %(default)s]')
    parser.add_argument_group(intl_optgroup)
    parser.add_argument('--debug-lib',
        action='store_true',
        dest='node_debug_lib',
        default=None,
        help='build lib with DCHECK macros')
    http2_optgroup.add_argument('--debug-nghttp2',
        action='store_true',
        dest='debug_nghttp2',
        default=None,
        help='build nghttp2 with DEBUGBUILD (default is false)')
    parser.add_argument_group(http2_optgroup)
    parser.add_argument('--without-dtrace',
        action='store_true',
        dest='without_dtrace',
        default=None,
        help='build without DTrace')
    parser.add_argument('--without-etw',
        action='store_true',
        dest='without_etw',
        default=None,
        help='build without ETW')
    parser.add_argument('--without-npm',
        action='store_true',
        dest='without_npm',
        default=None,
        help='do not install the bundled npm (package manager)')
    # Dummy option for backwards compatibility
    parser.add_argument('--without-report',
        action='store_true',
        dest='unused_without_report',
        default=None,
        help=argparse.SUPPRESS)
    parser.add_argument('--with-snapshot',
        action='store_true',
        dest='unused_with_snapshot',
        default=None,
        help=argparse.SUPPRESS)
    parser.add_argument('--without-snapshot',
        action='store_true',
        dest='unused_without_snapshot',
        default=None,
        help=argparse.SUPPRESS)
    parser.add_argument('--without-siphash',
        action='store_true',
        dest='without_siphash',
        default=None,
        help=argparse.SUPPRESS)
    # End dummy list.
    parser.add_argument('--without-ssl',
        action='store_true',
        dest='without_ssl',
        default=None,
        help='build without SSL (disables crypto, https, inspector, etc.)')
    parser.add_argument('--without-node-options',
        action='store_true',
        dest='without_node_options',
        default=None,
        help='build without NODE_OPTIONS support')
    parser.add_argument('--ninja',
        action='store_true',
        dest='use_ninja',
        default=None,
        help='generate build files for use with Ninja')
    parser.add_argument('--enable-asan',
        action='store_true',
        dest='enable_asan',
        default=None,
        help='compile for Address Sanitizer to find memory bugs')
    parser.add_argument('--enable-static',
        action='store_true',
        dest='enable_static',
        default=None,
        help='build as static library')
    parser.add_argument('--no-browser-globals',
        action='store_true',
        dest='no_browser_globals',
        default=None,
        help='do not export browser globals like setTimeout, console, etc. ' +
             '(This mode is not officially supported for regular applications)')
    parser.add_argument('--without-inspector',
        action='store_true',
        dest='without_inspector',
        default=None,
        help='disable the V8 inspector protocol')
    parser.add_argument('--shared',
        action='store_true',
        dest='shared',
        default=None,
        help='compile shared library for embedding node in another project. ' +
             '(This mode is not officially supported for regular applications)')
    parser.add_argument('--without-v8-platform',
        action='store_true',
        dest='without_v8_platform',
        default=False,
        help='do not initialize v8 platform during node.js startup. ' +
             '(This mode is not officially supported for regular applications)')
    parser.add_argument('--without-bundled-v8',
        action='store_true',
        dest='without_bundled_v8',
        default=False,
        help='do not use V8 includes from the bundled deps folder. ' +
             '(This mode is not officially supported for regular applications)')
    parser.add_argument('--verbose',
        action='store_true',
        dest='verbose',
        default=False,
        help='get more output from this script')
    parser.add_argument('--v8-non-optimized-debug',
        action='store_true',
        dest='v8_non_optimized_debug',
        default=False,
        help='compile V8 with minimal optimizations and with runtime checks')
    parser.add_argument('--v8-with-dchecks',
        action='store_true',
        dest='v8_with_dchecks',
        default=False,
        help='compile V8 with debug checks and runtime debugging features enabled')
    parser.add_argument('--v8-lite-mode',
        action='store_true',
        dest='v8_lite_mode',
        default=False,
        help='compile V8 in lite mode for constrained environments (lowers V8 '+
             'memory footprint, but also implies no just-in-time compilation ' +
             'support, thus much slower execution)')
    parser.add_argument('--v8-enable-object-print',
        action='store_true',
        dest='v8_enable_object_print',
        default=True,
        help='compile V8 with auxiliar functions for native debuggers')
    parser.add_argument('--node-builtin-modules-path',
        action='store',
        dest='node_builtin_modules_path',
        default=False,
        help='node will load builtin modules from disk instead of from binary')
    # Create compile_commands.json in out/Debug and out/Release.
    parser.add_argument('-C',
        action='store_true',
        dest='compile_commands_json',
        default=None,
        help=argparse.SUPPRESS)
    return(parser)

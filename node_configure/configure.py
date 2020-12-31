import args_parser
import util
import json
import os
import pipes
import pprint
from gyp.common import GetFlavor
import sys
#from gyp_node import run_gyp


def get_icu_versions(fn="tools/icu/icu_versions.json"):
    with open (fn) as f:
        icu_versions = json.load(f)
    return(icu_versions)


def get_flavor(options):
    flavor_params = {}
    if (options.dest_os):
        flavor_params['flavor'] = options.dest_os
    flavor = GetFlavor(flavor_params)  
    return(flavor)


def new_output():
    output = {
        'variables': {},
        'include_dirs': [],
        'libraries': [],
        'defines': [],
        'cflags': [],
    }
    return(output)

def config_libs(output,options):
    util.configure_library(options,'zlib', output)
    util.configure_library(options,'http_parser', output)
    util.configure_library(options,'libuv', output)
    util.configure_library(options,'brotli', output, pkgname=['libbrotlidec', 'libbrotlienc'])
    util.configure_library(options,'cares', output, pkgname='libcares')
    util.configure_library(options,'nghttp2', output, pkgname='libnghttp2')


def handle_ossfuzz_and_debug(output,options):
    output['variables']['ossfuzz'] = util.b(options.ossfuzz)
    variables = output['variables']
    del output['variables']
    variables['is_debug'] = util.B(options.debug)
    return(variables)

def handle_fips(output,options):
    config_fips = { 'make_global_settings' : [] }
    if 'make_fips_settings' in output:
        config_fips['make_global_settings'] = output['make_fips_settings']
        del output['make_fips_settings']
        write('config_fips.gypi', util.do_not_edit +pprint.pformat(config_fips, indent=2) + '\n',options)
    return(config_fips)


def handle_global_settings(output):
    if 'make_global_settings' in output:
        make_global_settings = output['make_global_settings']
        del output['make_global_settings']
    else:
        make_global_settings = False
    if make_global_settings:
        output['make_global_settings'] = make_global_settings
    return(make_global_settings)


####

def save_config_gypi(output,options,variables):
    output = {
      'variables': variables,
      'target_defaults': output,
    }
    util.print_verbose(output,options)
    util.write('config.gypi', util.do_not_edit +pprint.pformat(output, indent=2) + '\n',options)




def save_config_status( original_argv,options):
    util.write('config.status', '#!/bin/sh\nset -x\nexec ./configure ' +' '.join([pipes.quote(arg) for arg in original_argv]) + '\n',options)
    os.chmod('config.status', 0o775)



def save_config_mk(options,variables):
    config = {
      'BUILDTYPE': 'Debug' if options.debug else 'Release',
      'NODE_TARGET_TYPE': variables['node_target_type'],
    }
    #
    # Not needed for trivial case. Useless when it's a win32 path.
    if sys.executable != 'python' and ':\\' not in sys.executable:
      config['PYTHON'] = sys.executable

    if options.prefix:
      config['PREFIX'] = options.prefix

    if options.use_ninja:
      config['BUILD_WITH'] = 'ninja'
    #
    # On Windows there is another find.exe in C:\Windows\System32
    if sys.platform == 'win32':
      config['FIND'] = '/usr/bin/find'

    config_lines = ['='.join((k,v)) for k,v in config.items()]
    # Add a blank string to get a blank line at the end.
    config_lines += ['']
    config_str = '\n'.join(config_lines)
    # On Windows there's no reason to search for a different python binary.
    bin_override = None if sys.platform == 'win32' else util.make_bin_override()
    if bin_override:
      config_str = 'export PATH:=' + bin_override + ':$(PATH)\n' + config_str
    util.write('config.mk', util.do_not_edit + config_str,options)


def creat_gyp_args(options,flavor,args):
    gyp_args = ['--no-parallel', '-Dconfiguring_node=1']
    if options.use_ninja:
        gyp_args += ['-f', 'ninja']
    elif flavor == 'win' and sys.platform != 'msys':
        gyp_args += ['-f', 'msvs', '-G', 'msvs_version=auto']
    else:
        gyp_args += ['-f', 'make-' + flavor]
    if options.compile_commands_json:
        gyp_args += ['-f', 'compile_commands_json']
    # pass the leftover positional arguments to GYP
    gyp_args += args
    return(gyp_args)




import util
import configure
import os
import nodedownload
import args_parser
import sys
#node_version_h = "/mnt/sdb/NVNODE/node/src/node_version.h"
#node_napi_h = "/mnt/sdb/NVNODE/node/src/node_version.h"
#icu_current_ver_dep = "/mnt/sdb/NVNODE/node2/tools/icu/current_ver.dep"
#icu_versions_fn = "/mnt/sdb/NVNODE/node2/tools/icu/icu_versions.json"
#proj_dir = "/mnt/sdb/NVNODE/node2"
#original_argv = sys.argv[1:];


def configure(d):
    node_version_h = d.node_version_h;
    node_napi_h = d.node_napi_h;
    icu_current_ver_dep = d.icu_current_ver_dep;
    icu_versions_fn = d.icu_versions_fn;
    original_argv = d.original_argv
    ####
    if("with_intl" in d):
        options.with_intl = d.with_intl
    ####
    icu_versions= configure.get_icu_versions(icu_versions_fn)
    parser = args_parser.creat_parser(icu_versions)
    (options, args) = parser.parse_known_args()
    options.prefix = os.path.expanduser(options.prefix or '')
    auto_downloads = nodedownload.parse(options.download_list)
    ####
    flavor = configure.get_flavor(options)
    ####
    output = {
      'variables': {},
      'include_dirs': [],
      'libraries': [],
      'defines': [],
      'cflags': [],
    }
    util.check_compiler(output,options)
    util.configure_node(output,options,flavor,node_version_h)
    util.configure_napi(output,node_napi_h)
    util.configure_library(options,'zlib', output)
    util.configure_library(options,'http_parser', output)
    util.configure_library(options,'libuv', output)
    util.configure_library(options,'brotli', output, pkgname=['libbrotlidec', 'libbrotlienc'])
    util.configure_library(options,'cares', output, pkgname='libcares')
    util.configure_library(options,'nghttp2', output, pkgname='libnghttp2')
    util.configure_v8(output,options)
    util.configure_openssl(output,options)
    ####
    util.configure_intl(output,options,icu_versions,icu_current_ver_dep)
    util.configure_static(output,options)
    util.configure_inspector(output,options)
    util.configure_section_file(output,options)
    variables = configure.handle_ossfuzz_and_debug(output,options)
    config_fips = configure.handle_fips(output,options)
    configure.handle_global_settings(output)
    configure.save_config_gypi(output,options,variables);
    configure.save_config_status(original_argv,options);
    configure.save_config_mk(options,variables);
    configure.creat_gyp_args(options,flavor,args)
    ####
    if util.warn.warned and not options.verbose:
        util.warn('warnings were emitted in the configure phase')
    util.print_verbose("running: \n    " + " ".join(['python', 'tools/gyp_node.py'] + gyp_args),options)
    run_gyp(gyp_args)
    util.info('configure completed successfully')



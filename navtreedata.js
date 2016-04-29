var NAVTREE =
[
  [ "fplutil", "index.html", [
    [ "Prerequisites", "fplutil_prerequisites.html", [
      [ "Android SDK", "fplutil_prerequisites.html#fplutil_install_sdk", [
        [ "Linux", "fplutil_prerequisites.html#fplutil_install_sdk_linux", null ],
        [ "OSX / Windows", "fplutil_prerequisites.html#fplutil_install_sdk_osx_windows", null ]
      ] ],
      [ "Android NDK", "fplutil_prerequisites.html#fplutil_install_ndk", null ],
      [ "Python", "fplutil_prerequisites.html#fplutil_install_python", [
        [ "Linux", "fplutil_prerequisites.html#fplutil_install_python_linux", null ],
        [ "OSX / Windows", "fplutil_prerequisites.html#fplutil_install_python_osx_windows", null ]
      ] ],
      [ "Configure Command Line", "fplutil_prerequisites.html#fplutil_command_line", [
        [ "Linux", "fplutil_prerequisites.html#fplutil_command_line_linux", null ],
        [ "OSX", "fplutil_prerequisites.html#fplutil_command_line_osx", null ],
        [ "Windows", "fplutil_prerequisites.html#fplutil_command_line_windows", null ]
      ] ]
    ] ],
    [ "libfplutil", "libfplutil_overview.html", [
      [ "Using libfplutil_main", "libfplutil_main.html", [
        [ "Event Processing", "libfplutil_main.html#libfplutil_main_events", null ]
      ] ],
      [ "Using libfplutil_print", "libfplutil_print.html", [
        [ "Customizing the Log Tag", "libfplutil_print.html#libfplutil_print_tag", null ],
        [ "Configuring Buffering", "libfplutil_print.html#libfplutil_print_buffering", null ],
        [ "Redirecting Output", "libfplutil_print.html#libfplutil_print_redirection", null ]
      ] ],
      [ "Example", "libfplutil_example.html", [
        [ "Getting Started", "libfplutil_example.html#libfplutil_example_preparation", null ],
        [ "Building with fplutil", "libfplutil_example.html#libfplutil_example_build_fplutil", null ],
        [ "Building with ndk-build", "libfplutil_example.html#libfplutil_example_build_ndkbuild", null ]
      ] ],
      [ "Linking with Applications", "libfplutil_linking.html", [
        [ "Linking libfplutil_print", "libfplutil_linking.html#libfplutil_linking_print", null ]
      ] ],
      [ "API Reference", "usergroup0.html", [
        [ "libfplutil_main", "main_8h.html", null ],
        [ "libfplutil_print", "print_8h.html", null ]
      ] ]
    ] ],
    [ "android_ndk_perf.py", "android_ndk_perf.html", [
      [ "Sampling vs. Intrusive Profiling", "android_ndk_perf.html#android_ndk_perf_sampling", null ],
      [ "Building Applications for Profiling", "android_ndk_perf.html#android_ndk_perf_building", [
        [ "Building and Installing using build_all_android.py", "android_ndk_perf.html#android_ndk_perf_building_fplutil", null ],
        [ "Building using ndk-build and ant", "android_ndk_perf.html#android_ndk_perf_building_manual", null ]
      ] ],
      [ "Capturing a Trace", "android_ndk_perf.html#android_ndk_perf_record", null ],
      [ "Visualizing a Trace", "android_ndk_perf.html#android_ndk_perf_visualize", null ],
      [ "Trace Reports", "android_ndk_perf.html#android_ndk_perf_report", null ]
    ] ],
    [ "build_all_android.py", "build_all_android.html", [
      [ "Building Applications", "build_all_android.html#build_all_android_build", null ],
      [ "Signing Applications", "build_all_android.html#build_all_android_sign", [
        [ "Signing with Keys", "build_all_android.html#build_all_android_sign_key", null ]
      ] ],
      [ "Installing Applications", "build_all_android.html#build_all_android_install", null ],
      [ "Running Applications", "build_all_android.html#build_all_android_run", null ],
      [ "Build Configuration", "build_all_android.html#build_all_android_build_config", null ],
      [ "Cleaning Build Artifacts", "build_all_android.html#build_all_android_clean", null ],
      [ "Working with Multiple Devices", "build_all_android.html#build_all_android_multiple_devices", null ]
    ] ],
    [ "buildutil", "buildutil_overview.html", [
      [ "Examples", "buildutil_examples.html", [
        [ "Android", "buildutil_examples.html#buildutil_examples_android", null ],
        [ "Android Code", "buildutil_examples_android_code.html", null ],
        [ "Linux", "buildutil_examples.html#buildutil_examples_linux", null ],
        [ "Linux Code", "buildutil_examples_linux_code.html", null ]
      ] ],
      [ "API Reference", "buildutil_api_reference.html", [
        [ "common.py", "common_8py.html", [
          [ "buildutil.common.Error", "classfplutil_1_1buildutil_1_1common_1_1_error.html", null ],
          [ "buildutil.common.ToolPathError", "classfplutil_1_1buildutil_1_1common_1_1_tool_path_error.html", null ],
          [ "buildutil.common.SubCommandError", "classfplutil_1_1buildutil_1_1common_1_1_sub_command_error.html", null ],
          [ "buildutil.common.ConfigurationError", "classfplutil_1_1buildutil_1_1common_1_1_configuration_error.html", null ],
          [ "buildutil.common.AdbError", "classfplutil_1_1buildutil_1_1common_1_1_adb_error.html", null ],
          [ "buildutil.common.BuildEnvironment", "classfplutil_1_1buildutil_1_1common_1_1_build_environment.html", null ]
        ] ],
        [ "android.py", "android_8py.html", [
          [ "buildutil.android.XMLFile", "classfplutil_1_1buildutil_1_1android_1_1_x_m_l_file.html", null ],
          [ "buildutil.android.AndroidManifest", "classfplutil_1_1buildutil_1_1android_1_1_android_manifest.html", null ],
          [ "buildutil.android.BuildXml", "classfplutil_1_1buildutil_1_1android_1_1_build_xml.html", null ],
          [ "buildutil.android.AdbDevice", "classfplutil_1_1buildutil_1_1android_1_1_adb_device.html", null ],
          [ "buildutil.android.BuildEnvironment", "classfplutil_1_1buildutil_1_1android_1_1_build_environment.html", null ]
        ] ],
        [ "linux.py", "linux_8py.html", [
          [ "buildutil.linux.BuildEnvironment", "classfplutil_1_1buildutil_1_1linux_1_1_build_environment.html", null ]
        ] ]
      ] ]
    ] ],
    [ "readme", "md_readme.html#fplutil_readme", null ],
    [ "contributing", "contributing.html", null ]
  ] ]
];

var NAVTREEINDEX =
[
"android_8py.html"
];

var SYNCONMSG = 'click to disable panel synchronisation';
var SYNCOFFMSG = 'click to enable panel synchronisation';
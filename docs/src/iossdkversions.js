/*
 * Copyright 2016 Google Inc. All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// This file can be included in doxygen markdown files to handle iOS SDK
// versioning -- specifically, building SDL which requires the `-sdk` flag.
//
// USAGE:
//    To use this file in your doxygen markdown files, you will need to
//    do the following:
//
//      1. In your `doxyfile`, edit the `HTML_EXTRA_FILES` to contain
//         both `iossdkversions.js` and `tested_ios_sdk_versions.json`.
//
//         For example:
//
//           HTML_EXTRA_FILES = $(SHARED_DOCS_PATH)/iossdkversions.js \
//                              $(SHARED_DOCS_PATH)/tested_ios_sdk_versions.json
//
//      2. In your markdown file, add the following toward the top of your file:
//
//           \htmlonly
//           <script src="iossdkversions.js"></script>
//           \endhtmlonly
//
//    At this point, you will have full access to the functionality of this
//    file. There are two main things that this file accomplishes for you:
//
//      1. It can generate an HTML `<select>` tag that is templated with all
//         of the tested iOS SDK versions in `tested_ios_sdk_versions.json`.
//
//         To use this inside your markdown file, simply create a `<div>` tag
//         with an `id` of `ios-sdk-version-select`, and the JavaScript will
//         handle the rest.
//
//         For example:
//
//           In your markdown file:
//
//             `<div id="ios-sdk-version-select"></div>`
//
//           Will generated the following in your resulting HTML page:
//
//             Please select your iOS SDK version from the list of tested
//             versions to automatically customize the following commands for
//             your machine: [drop-down-menu-goes-here]
//
//      2. It can also generate the code snippet used to build SDL, templated
//         with the correct `-sdk iphonesimulatorXXX` command for the selected
//         iOS SDK version from the `<select>` drop-down.
//
//         To use this inside of your markdown file, simply create a `<div>` tag
//         with an `id` of `build-sdl-iphonesimulator-code`, and the JavaScript
//         will handle the rest.
//
//         For example:
//
//           In your markdown file:
//
//             <div id="build-sdl-iphonesimulator-code"></div>
//
//           Let's say that the user selected `iOS 8.3` from the `<select>`
//           drop-down menu, then this will generate the following in your
//           resulting HTML page (formatting the code segments appropriately):
//
//             <code>
//               cd ../sdl
//               xcodebuild ARCHS="x86_64 i386" -project Xcode-iOS/SDL/SDL.xcodeproj -sdk iphonesimulator8.3 build
//             </code>
//             <br>
//             <i>
//               Note: The `-sdk` flag must match with an installed version of
//               the iphone simulator. If you selected the appropriate iOS SDK
//               version from the drop-down menu above, then this command should
//               be correct. Otherwise, to view all of the iOS Simulator SDKs
//               installed on your machine, run `xcodebuild -showsdks`. The last
//               section labeled `iOS Simulator SDKs` will show you the name of
//               each simulator, followed by the corresponding `-sdk` command.
//             </i>


/**
 * Check if an HTML `class` attribute is in the iOS version-specific format.
 * @param {string} versionClass An HTML `class` attribute in the format
 * 'iOS {version}', where {version} is an iOS SDK version number
 * (e.g. '8.3').
 * @return {boolean} Returns `true` if `versionClass` was in the valid
 * format, prefixed with 'iOS '. Otherwise, it returns false.
 */
function isVersionClassName(versionClass) {
  if (versionClass && versionClass.substring(0, 4) == 'iOS ' &&
      versionClass.length > 4) {
    return true;
  } else {
    return false;
  }
}

/**
 * Hide every HTML element with an iOS SDK version class attribute, except for
 * the class that is selected by the iOS SDK version `select` drop-down menu.
 */
function displaySdkVersion() {
  var selection = $('select').val();

  var htmlElements = document.getElementsByTagName('*');
  for (var i = 0; i < htmlElements.length; i++) {
    if (isVersionClassName(htmlElements[i].className)) {
      if (htmlElements[i].className != selection) {
        htmlElements[i].style.display = 'none';
      } else {
        htmlElements[i].style.display = 'initial';
      }
    }
  }
}

/**
 * Gets the HTML DOM element with the id of `ios-sdk-version-select` and
 * populates it with a <select> drop-down menu, which will be populated
 * with the iOS SDK versions from `tested_ios_sdk_versions.json`.
 */
 function createSelectElement() {
  var select = document.getElementById('ios-sdk-version-select');
  select.innerHTML = 'Please select your iOS SDK version from the list of ' +
                     'tested versions to automatically customize the ' +
                     'following commands for your machine:&nbsp;&nbsp;' +
                     '<select id="sdk-options" onchange=' +
                     '"displaySdkVersion()"></select><br><br>';
 }

/**
 * Parse the iOS SDK versions from a JSON file and add them to the list to
 * select from in the `select` drop-down menu. Then display the first one
 * as the default.
 * @param {PlainObject} data Contains the JSON data describing the iOS SDk
 * version and simulator values.
 */
function parseSdkVersionsJson(data) {
  createSelectElement();

  var optionsHTML = '';
  var simulatorHTML = '<div class="fragment">';

  for (var i = 0; i < data.sdks.length; i++) {
    var version = data.sdks[i].version;
    var simulator = data.sdks[i].simulator;

    optionsHTML += '<option value="' + version + '">' + version +
      '</option>';
    simulatorHTML += '<div class="' + version + '">' +
      '<div class="line">cd ../sdl</div><div class="line">xcodebuild ' +
      'ARCHS="x86_64 i386" -project Xcode-iOS/SDL/SDL.xcodeproj -sdk ' +
      simulator + ' build</div></div>';
  }

  simulatorHTML += '</div><i>Note: The <code>-sdk</code> flag must match ' +
                   'with an installed version of the iphone simulator. If ' +
                   'you selected the appropriate iOS SDK version from the ' +
                   'drop-down menu above, then this command should be ' +
                   'correct. Otherwise, to view all the iOS Simulator SDKs ' +
                   'installed on your machine, run <code>xcodebuild -showsdks' +
                   '</code>. The last section labeled <code>iOS Simulator ' +
                   'SDKs</code> will show you the name of each simulator, ' +
                   'followed by the corresponding <code>-sdk</code> command.' +
                   '</i>';

  document.getElementById('sdk-options').innerHTML = optionsHTML;
  document.getElementById('build-sdl-iphonesimulator-code').innerHTML =
      simulatorHTML;

  // Hide all of the versions except for the first one, by default. This will
  // change dynmaically as users click options from the `select` drop-down menu.
  displaySdkVersion();
}

$(function() {
  jQuery.getJSON('tested_ios_sdk_versions.json', parseSdkVersionsJson);
});


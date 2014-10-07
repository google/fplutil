@echo off
@rem Copyright 2014 Google Inc. All rights reserved.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem     http://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.

@rem NOTE: This requires https://github.com/Feneric/doxypypy which filters
@rem python doc strings so they're understood by doxygen.
@rem
@rem git clone https://github.com/Feneric/doxypypy
@rem cd doxypypy
@rem python -m setup install
@rem
python -m doxypypy.doxypypy -a -c %1

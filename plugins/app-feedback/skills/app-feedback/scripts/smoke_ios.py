"""Vendor the documented example into a new SwiftUI iOS app and build both configurations."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if sys.platform != 'darwin' or not output.is_relative_to('/Volumes/eyedisk/build'):
        parser.error('requires macOS and --output below /Volumes/eyedisk/build')
    if not Path('/Volumes/eyedisk').is_dir() or not shutil.which('xcodegen'):
        parser.error('requires mounted eyedisk and an existing XcodeGen installation')
    output.mkdir(parents=True, exist_ok=False)
    skill = Path(__file__).resolve().parents[1]
    shutil.copytree(skill / 'assets/AppFeedback', output / 'Vendor/AppFeedback')
    reference = (skill / 'references/integration.md').read_text()
    source = reference.split('```swift\n', 1)[1].split('\n```', 1)[0]
    (output / 'Sources').mkdir()
    (output / 'Sources/ExampleApp.swift').write_text(source + '\n')
    (output / 'project.yml').write_text('''name: FeedbackExample
options:
  deploymentTarget:
    iOS: "17.0"
packages:
  AppFeedback:
    path: Vendor/AppFeedback
settings:
  base:
    SWIFT_VERSION: "6.0"
    CODE_SIGNING_ALLOWED: NO
    GENERATE_INFOPLIST_FILE: YES
    MARKETING_VERSION: "1.0"
    CURRENT_PROJECT_VERSION: "1"
    INFOPLIST_KEY_UILaunchScreen_Generation: YES
    INFOPLIST_KEY_UISupportedInterfaceOrientations: UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight
    TARGETED_DEVICE_FAMILY: "1,2"
targets:
  FeedbackExample:
    type: application
    platform: iOS
    sources: [Sources]
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.example.feedback-smoke
    dependencies:
      - package: AppFeedback
''')
    environment = dict(os.environ)
    for name, folder in [('TMPDIR', 'tmp'), ('CLANG_MODULE_CACHE_PATH', 'modules'),
                         ('SWIFTPM_MODULECACHE_OVERRIDE', 'modules'), ('XDG_CACHE_HOME', 'cache')]:
        (output / folder).mkdir(exist_ok=True)
        environment[name] = str(output / folder)
    results = []

    def run(name, command):
        proc = subprocess.run(command, cwd=output, env=environment, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / (name + '.log')).write_text(proc.stdout)
        warnings = len(re.findall(r'\bwarning:', proc.stdout))
        results.append(dict(name=name, command=command, exit=proc.returncode, warnings=warnings))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(f'{name}: exit={proc.returncode}, warnings={warnings}', flush=True)
        if proc.returncode or warnings:
            raise RuntimeError(f'see {output / (name + ".log")}')

    run('generate-project', ['xcodegen', 'generate', '--spec', str(output / 'project.yml')])
    for configuration in ['Debug', 'Release']:
        command = ['xcodebuild', '-project', str(output / 'FeedbackExample.xcodeproj'), '-scheme', 'FeedbackExample',
                   '-configuration', configuration, '-destination', 'generic/platform=iOS Simulator',
                   '-derivedDataPath', str(output / 'DerivedData'), '-clonedSourcePackagesDirPath', str(output / 'packages'),
                   'build']
        if shutil.which('eyebuild'):
            command = ['eyebuild', '-p', 'oozoofrog-plugin', 'run', 'app-feedback-validation', '--'] + command
        run(configuration.lower() + '-build', command)
    print('The skill example builds in an independent app; this does not verify Mail delivery or UI appearance.')


if __name__ == '__main__':
    main()

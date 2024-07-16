import subprocess
import os
from pathlib import Path
import sys
import json
import polib
import shutil
import argparse
from collections import OrderedDict

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def get_translation_stats(in_filename):
    #command = ["msgfmt", "--statistics", in_filename]
    #result = subprocess.run(command, capture_output=True, text=True)
    #output = result.stderr.strip()

    #parts = output.split(',')
    #stats = {}
    #for part in parts:
    #    #print(f"Got: {part}")
    #    stats_tmp = part.strip().split(' ', 1)
    #    number = stats_tmp[0]
    #    category = stats_tmp[1].split(' ')[0]
    #    stats[category] = int(number)
    #eprint(f"Processing {in_filename}")
    po = polib.pofile(in_filename)
    stats = {}
    stats['translated'] = len(po.translated_entries())
    stats['fuzzy'] = len(po.fuzzy_entries())
    stats['untranslated'] = len(po.untranslated_entries())

    return {
        'translated': stats.get('translated', 0),
        'fuzzy': stats.get('fuzzy', 0),
        'untranslated': stats.get('untranslated', 0)
    }

def is_internal_file(filename: str):
    if "_caligraph" in filename or "-dummy" in filename or "-anthropic" in filename:
        return True
    return False

def process_translation_stats(template_folder: str, localized_folder: str):
    results = []
    #eprint(f"Processing {template_folder} | {localized_folder}")
    for subfolder in os.scandir(template_folder):
        if subfolder.is_dir():
            for file in Path(subfolder).glob('*.pot'):
                if is_internal_file(str(file)):
                    eprint(f"File {str(file)} is internal caligraph, ignoring.")
                    continue
                relative_path = os.path.relpath(file, template_folder)
                path_in_localized_folder = os.path.join(localized_folder, relative_path[:-4] + '.po')
                report_path = relative_path

                if os.path.exists(path_in_localized_folder):
                    stats = get_translation_stats(path_in_localized_folder)
                    report_path = relative_path[:-4] + '.po'
                else:
                    stats = get_translation_stats(str(file))

                results.append({"file": report_path, "stats": stats})

    results.sort(key=lambda x: x["file"])
    return results

def translate_all(template_folder: str, localized_folder: str):
    for file in Path(template_folder).glob('*.pot'):
        if is_internal_file(str(file)):
            eprint(f"File {str(file)} is internal caligraph, ignoring.")
            continue
        relative_path = os.path.relpath(file, template_folder)
        path_in_localized_folder = os.path.join(localized_folder, relative_path[:-4] + '.po')
        log_filename = os.path.join(localized_folder, relative_path[:-4] + '.log')
        log_err_filename = os.path.join(localized_folder, relative_path[:-4] + '.err')

        needs_translated = False

        if not os.path.exists(path_in_localized_folder):
            eprint(f"File {path_in_localized_folder} does not exist, copying it from template, and translating it.")
            shutil.copyfile(str(file), path_in_localized_folder)
            needs_translated = True
        
        if not needs_translated:
            translation_stats = get_translation_stats(path_in_localized_folder)
            if translation_stats['fuzzy'] > 0 or translation_stats['untranslated'] > 0:
                needs_translated = True

        if not needs_translated:
            eprint(f"File {path_in_localized_folder} does not needs further translating.")
            continue

        eprint(f"Translating {path_in_localized_folder}... and writing log to {log_filename}")
        command = ["bash", "/home/htruong/develop/caligraph-translate-api/translate-gettext.sh", path_in_localized_folder]
        result = subprocess.run(command, capture_output=True)
        with open(log_filename, "wb") as log_file:
            log_file.write(result.stdout)
        with open(log_err_filename, "wb") as log_err_file:
            log_err_file.write(result.stderr)


def main():
    parser = argparse.ArgumentParser(description="Process translation files.")
    parser.add_argument('--action', choices=['filestats', 'translate'], required=True, help="Action to perform")
    parser.add_argument('localized_folder', help="Path to the localized folder to process")
    parser.add_argument('template_folder', help="Path to the template folder to process")

    args = parser.parse_args()

    if args.action == 'filestats':
        results = process_translation_stats(args.template_folder, args.localized_folder)
        print(json.dumps(results, indent=2))
    elif args.action == 'translate':
        translate_all(args.template_folder, args.localized_folder)
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1)

if __name__ == "__main__":
    main()
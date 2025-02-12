import argparse
import json
import os
import shutil
import logging

import coloredlogs
import sys
from basset.exceptions import *

class Merger:
    def __init__(self):
        self.source_assets_dir = ""
        self.default_xcasset_dir = ""
        coloredlogs.install()

    def get_selected_xcassets_dir(self):
        xcassets_list = []
        selected_xcassets = None
        for path, subdirectories, files in os.walk(os.getcwd()):
            if path.endswith(".xcassets") and os.path.isdir(path):
                xcassets_list.append(os.path.relpath(path, os.getcwd()))

        logging.info("Found xcassets:")
        for single_xcasset in xcassets_list:
            logging.info("  " + single_xcasset)

        xcassets_count = len(xcassets_list)
        if xcassets_count == 0:
            raise NoXCAssetsFoundException()
        elif xcassets_count == 1:
            selected_xcassets = xcassets_list[0]
        elif xcassets_count >= 2:
            if self.default_xcasset_dir in xcassets_list:
                selected_xcassets = self.default_xcasset_dir
            else:
                raise NoDefaultXCAssetFoundException(xcassets_count)
        return selected_xcassets

    def merge(self):
        self.source_assets_dir = self.source_assets_dir.rstrip('\\/')
        self.default_xcasset_dir = self.default_xcasset_dir.rstrip('\\/')

        self.source_assets_dir = os.path.expandvars(os.path.expanduser(self.source_assets_dir))
        self.default_xcasset_dir = os.path.expandvars(os.path.expanduser(self.default_xcasset_dir))

        logging.info("Merging assets from {0} using {1} as default xcassets".format(self.source_assets_dir,
                                                                                    self.default_xcasset_dir))

        destination_xcassets_dir = self.get_selected_xcassets_dir()
        logging.info("Selected " + destination_xcassets_dir + " xcasset")

        merged_files_count = 0
        for path, subdirectories, files in os.walk(self.source_assets_dir):
            for filename in files:
                logging.info("Trying to merge: " + filename)
                if filename.lower().endswith(".pdf"):
                    basename = filename.split(".")[0]
                    asset_name = basename

                    asset_dir_in_destination_xcasset = os.path.join(destination_xcassets_dir,
                                                                    os.path.relpath(path, self.source_assets_dir),
                                                                    asset_name + ".imageset")
                    if not os.path.isdir(asset_dir_in_destination_xcasset):
                        os.makedirs(asset_dir_in_destination_xcasset)

                    # Create / update JSON file
                    content_json_file_path = os.path.join(asset_dir_in_destination_xcasset, "Contents.json")

                    contents_json = {
                        "images": [],
                        "info": {
                            "version": 1,
                            "author": "xcode",
                        }
                    }

                    if os.path.isfile(content_json_file_path):
                        with open(content_json_file_path, "r") as data_file:
                            contents_json = json.load(data_file)

                    contents_json["images"] = [
                        {
                            "idiom": "universal",
                            "filename": filename
                        }
                    ]

                    with open(content_json_file_path, "w+") as data_file:
                        json.dump(contents_json, data_file, indent=1)

                    # Copy image
                    destination_path = os.path.join(asset_dir_in_destination_xcasset, filename)
                    source_path = os.path.join(os.getcwd(), path, filename)
                    if not os.path.exists(destination_path):
                        shutil.copy2(source_path, destination_path)
                        logging.info("Copied to {0}".format(destination_path))
                    else:
                        logging.info("Skipping {0}, it already exists".format(destination_path))

                    logging.info("Merged " + source_path)
                    merged_files_count += 1
                elif filename.lower().endswith(".png") or filename.lower().endswith(".jpg"):
                    basename = filename.split(".")[0]

                    if basename[-3:] in ["@2x", "@3x"]:
                        asset_scale = basename[-2:]
                        asset_name = basename[:-3]
                    else:
                        asset_scale = "1x"
                        asset_name = basename

                    asset_dir_in_destination_xcasset = os.path.join(destination_xcassets_dir,
                                                                    os.path.relpath(path, self.source_assets_dir),
                                                                    asset_name + ".imageset")
                    if not os.path.isdir(asset_dir_in_destination_xcasset):
                        os.makedirs(asset_dir_in_destination_xcasset)

                    # Create / update JSON file
                    content_json_file_path = os.path.join(asset_dir_in_destination_xcasset, "Contents.json")

                    contents_json = {
                        "images": [],
                        "info": {
                            "version": 1,
                            "author": "xcode",
                        }
                    }

                    if os.path.isfile(content_json_file_path):
                        with open(content_json_file_path, "r") as data_file:
                            contents_json = json.load(data_file)

                    image_found = False

                    for index, scaled_image_dict in enumerate(contents_json["images"]):
                        needed_keys_present = all(k in scaled_image_dict for k in ("idiom", "scale"))
                        if needed_keys_present:
                            is_universal_asset_with_scale = scaled_image_dict["idiom"] == "universal" and \
                                                            scaled_image_dict["scale"] == asset_scale
                            if is_universal_asset_with_scale:
                                contents_json["images"][index]["filename"] = filename
                                image_found = True

                    if not image_found:
                        contents_json["images"].append(
                            {
                                "idiom": "universal",
                                "scale": asset_scale,
                                "filename": filename
                            }
                        )

                    with open(content_json_file_path, "w+") as data_file:
                        json.dump(contents_json, data_file, indent=1)

                    # Copy image
                    destination_path = os.path.join(asset_dir_in_destination_xcasset, filename)
                    source_path = os.path.join(os.getcwd(), path, filename)
                    shutil.copy2(source_path, destination_path)
                    logging.info("Merged " + source_path)
                    merged_files_count += 1
                else:
                    logging.info("file skipped xcassets from merging: " + filename.lower())

        logging.info("Finished merging with xcassets folder. Merged " + str(merged_files_count) + " files.")

def main(args_to_parse):
    parser = argparse.ArgumentParser(description='Converts raw assets to proper PNG(s).')
    parser.add_argument('-a', '--assets_dir', default="./GeneratedAssets",
                        help='path to directory with generated assets')
    parser.add_argument('-d', '--default_xcassets_dir', default="./Assets.xcassets",
                        help='path to default XCAssets directory')
    parsed_args = parser.parse_args(args_to_parse)

    merger = Merger()
    merger.source_assets_dir = parsed_args.assets_dir
    merger.default_xcasset_dir = parsed_args.default_xcasset_dir
    Merger.merge()

if __name__ == '__main__':
    args = sys.argv[1:]
    main(args)

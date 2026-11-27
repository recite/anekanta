#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import csv
import logging
import os
import re

import ftfy
from anekanta.matching import author_year_pattern, split_sentences
from anekanta.pdf_text import cached_text, read_pdf

__version__ = "0.0.1"


LOG_FILE = "autosumpdf.log"

DEF_IN_CSV = "output.csv"
DEF_OUT_CSV = "autosum-output.csv"
DEF_TXT_DIR = "txt"


def setup_logger(level=logging.DEBUG):
    """Set up logging"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(message)s",
        datefmt="%m-%d %H:%M",
        filename=LOG_FILE,
        filemode="a",
    )
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter("%(levelname)-8s %(message)s")
    console.setFormatter(formatter)
    logging.getLogger("").addHandler(console)


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-i",
        "--input",
        action="store",
        dest="input",
        default=DEF_IN_CSV,
        help="CSV input filename",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        dest="output",
        default=DEF_OUT_CSV,
        help="CSV output filename",
    )
    parser.add_argument(
        "-t",
        "--text",
        action="store",
        dest="txt_dir",
        default=DEF_TXT_DIR,
        help="extract to specific directory",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="force extract text file if exists",
    )
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument(
        "-a1",
        "--author-1-lastname",
        action="store",
        help="1st author of citation",
        dest="author1",
    )
    parser.add_argument(
        "-a2",
        "--author-2-lastname",
        action="store",
        help="2nd author of citation",
        dest="author2",
    )
    parser.add_argument(
        "-y", "--year", action="store", help="Year of publication", dest="year"
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    parser.add_argument(
        "-r",
        "--regex",
        action="store",
        help="specify custom regex to filter citations.",
        dest="regex",
    )

    results = parser.parse_args()

    if results.author1 is None and results.regex is None:
        parser.error(
            "Specify an author (-a1) or a citation regular expression (-r)."
        )

    return results


def build_regexp_list(args):
    """
    builds a list of regexps to be used for filtering citations using available
    information like first, second author and year (command line arguments -a1,
    -a2 and y) and /or the custom regexp (-r).
    """
    exp_list = []

    if args.author1 is not None:
        if args.year is None:
            year = ""
            exp_list.append(re.escape(args.author1) + r"\set al\.")
        else:
            year = re.escape(args.year)
            exp_list.append(author_year_pattern(args.author1, args.year))
        if args.author2 is not None:
            exp_list.append(
                re.escape(args.author1)
                + r"(\,){0,1}\s{0,1}(and|&){0,1}\s"
                + re.escape(args.author2)
                + r"\,{0,1}\s{0,1}"
                + year
            )

    if args.regex is not None:  # custom regexp
        exp_list.append(args.regex)

    return exp_list


def search_citation(text, exp):
    """Finds sentences around citations, where the regexp `exp matches"""

    lines = text.split("\n")
    text = " ".join(lines)
    text = " ".join(text.split())
    text = ftfy.fix_text(text)
    logging.info("Search...'{0!s}'".format(exp))

    sentences = split_sentences(text)
    regex = re.compile(exp, flags=(re.I))

    founds = set()
    for sent in sentences:
        if regex.search(sent):
            founds.add(sent)
    return founds


if __name__ == "__main__":
    args = get_args()
    regexp_list = build_regexp_list(args)
    if args.verbose:
        setup_logger(logging.DEBUG)
    else:
        setup_logger(logging.INFO)
    output = []

    if not os.path.exists(args.txt_dir):
        logging.info(
            "Create text files directory... ({0!s})".format(args.txt_dir)
        )
        os.makedirs(args.txt_dir, exist_ok=True)
    else:
        logging.info(
            "Current text files directory... ({0!s})".format(args.txt_dir)
        )

    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            pdf_path = r["pdf_path"]
            try:
                pdf_bytes, digest = read_pdf(pdf_path)
                text = cached_text(
                    pdf_bytes, digest, args.txt_dir, force=args.force
                )
                founds = set()
                for regexp in regexp_list:
                    results = search_citation(text, regexp)
                    founds.update(results)
                    logging.info(
                        "Regex: '{0!s}', Found: {1:d}".format(
                            regexp, len(results)
                        )
                    )
                r["founds"] = "\n".join(sorted(founds))
                r["status"] = "OK"
            except Exception as e:
                logging.error(e)
                r["founds"] = ""
                r["status"] = "ERROR"
            output.append(r)

    logging.info("Save output to file...'{0!s}'".format(args.output))
    with open(args.output, "w", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "url",
                "title",
                "authors",
                "summary",
                "cited_by",
                "pdf_url",
                "pdf_path",
                "founds",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(output)

    logging.info("Done!")

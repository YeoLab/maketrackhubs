#!/usr/bin/env python
'''
Created on June 10, 2023

@author: byee4

Given a list of * files makes trackhubs for those files

Assumes that you have an aws profile that is configured with access to yeolab's trackhub bucket.

'''
import logging
import argparse
import re
import os
from itertools import groupby
import subprocess
import time
from trackhub import Hub, GenomesFile, Genome, TrackDb, Track, AggregateTrack, SuperTrack, helpers
from pathlib import Path
from trackhub.upload import upload_hub

import boto3
import botocore

PROFILE = 'yeolab-trackhubs'

def remove_plus_and_pct(string):
    """
    Args:
        string:
    Returns: string after removing all + and all % characters
    """
    clean_string = string.replace('+','').replace('%','')
    return clean_string


def copy_file_to_aws(src, bucket, subdir):
    """
    Copies a file from local to AWS

    :param fn: basestring
        filename of the object that needs to be downloaded.
    :param bucket: basestring
        bucket name (minus the s3:// prefix)
    :param output_dir: basestring
        output directory where the rawdata should go.
    :return:
    """

    session = boto3.Session(profile_name=PROFILE)
    s3client = session.client(
        's3',
    )

    try:
        s3client.upload_file(
            src, bucket, os.path.join(subdir, os.path.basename(src)), ExtraArgs={'ACL': 'public-read'}
        )
        print("Done uploading {} to aws ({})".format(src, bucket))
    except Exception as e:
        print(e)
        return 1


def copy_dir_to_aws(src, dest):
    """
    Copies a directory from local to AWS

    :param src: basestring
        local source filename
    :param bucket: basestring
        aws s3 bucket name
    :return:
    """
    if not dest.startswith('s3://'):
        dest = 's3://' + dest
    if not dest.endswith('/'):
        dest = dest + '/'
        
    if not src.endswith('/'):
        src = src + '/'

    cmd = 'aws s3 cp {} {} --recursive --profile {}'.format(
        src,
        os.path.join(dest),
        PROFILE
    )
    print("AWS UPLOAD COMMAND: {}".format(cmd))
    try:
        print("Uploading to aws: {}".format(cmd))
        ret = subprocess.check_call(cmd, shell=True)
        print("Done uploading {} to aws ({}) with a return code of: {}".format(src, dest, ret))
        time.sleep(1)
    except Exception as e:
        print(e)
        return 1


if __name__ == "__main__":
    main()


def main():
    parser = argparse.ArgumentParser(description='Takes in files to turn into trackhub. This version automatically ')

    # tracks files
    ##############
    parser.add_argument('files', nargs='+', help='Files to turn into track hub')

    # namings
    #########
    parser.add_argument('--hub',    help="hub name (no spaces)", required=True)
    parser.add_argument('--genome', help="genome name",          required=True)

    # upload (in fact run_local=True)
    ########
    #parser.add_argument('--no_s3', default=False, action="store_true", help="upload to defined server instead of s3")
    #parser.add_argument('--serverscp', default="tscc-login2.sdsc.edu", help="server to SCP to")
    #parser.add_argument('--user', default='adomissy', help="that is uploading files")
    # parser.add_argument('--uploaddir', default='yeolab-trackhubs', help="directory to upload files to if not uploading to aws")

    # web access
    ############
    # parser.add_argument('--urldomain', default="s3-us-west-2.amazonaws.com", help="url domain for public access to trackhubs")
    # parser.add_argument('--urldir',    default="yeolab-trackhubs", help="url directory for public access to trackhubs")

    # hub labels
    ############
    # parser.add_argument('--hub_short_label', default=None, help="short label for hub")
    # parser.add_argument('--hub_long_label',  default=None, help="long label for hub")
    parser.add_argument('--hub_email',       default='bay001@ucsd.edu', help="email for hub")

    # name parts grouping
    #####################
    parser.add_argument('--sep', default=".", help="Seperator")
    parser.add_argument('--num_sep', default=2, type=int, help="Number of seperators deep to group on")


    ###########################################################################
    args = parser.parse_args()

    # Let's keep all trackhubs here for now.
    urldomain = "s3-us-west-2.amazonaws.com"
    urldir = "yeolab-trackhubs"
    uploaddir = "yeolab-trackhubs"
    hub_name = args.hub
    hub_email = args.hub_email

    # setup logger
    logger = logging.getLogger('maketrackhubs')
    logger.setLevel(logging.INFO)
    ih = logging.FileHandler('maketrackhubs.log')
    eh = logging.FileHandler('maketrackhubs.err')
    ih.setLevel(logging.INFO)
    eh.setLevel(logging.ERROR)
    logger.addHandler(ih)
    logger.addHandler(eh)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ih.setFormatter(formatter)
    eh.setFormatter(formatter)
    logger.info("starting program")
    
    
    # default label settings
    ########################
    hub_short_label = hub_name
    hub_long_label = hub_name

    # hard coding serverscp, in variable HOST
    HOST="localhost"
    # hard coding user, in variable USER
    USER="user"

    GENOME = args.genome
    # hack for tutorial dataset so it is easy to view in ucsd genome browser
    if GENOME == 'hg19chr19kbp255':
        GENOME == 'hg19'

    uploaddir = os.path.join(uploaddir, hub_name)

    URLBASE = os.path.join("http://" + urldomain + "/" + urldir + "/", hub_name)

    # create data structures
    ########################

    hub = Hub(hub=hub_name,
              short_label=hub_short_label,
              long_label=hub_long_label,
              email=hub_email,
    )
    hub.upload_fn = uploaddir

    genomes_file = GenomesFile()
    hub.add_genomes_file(genomes_file)

    genome = Genome(GENOME)
    genomes_file.add_genome(genome)

    trackdb = TrackDb()
    genome.add_trackdb(trackdb)

    supertrack = SuperTrack(
        name=hub_name,
        short_label=hub_short_label,
        long_label=hub_long_label
    )

    # separate bigwigs, bigbeds and others for different processing methods
    #######################################################################

    bigwig_files = [file for file in args.files if file.endswith(".posbw") or file.endswith(".negbw") or file.endswith(".bw") or file.endswith(".bigWig")or file.endswith(".bigwig")]
    bigbed_files = [file for file in args.files if file.endswith(".bb") or file.endswith(".bigBed") or file.endswith(".bigbed")]

    # not used
    #other_files = [file for file in args.files if (file not in bigwig_files and file not in bigbed_files )]

    # process bigwig files , re-grouped by third 2 dot-sepatarated name-parts, as multitracks
    ##########################################################################################
    key_func = lambda x: os.path.basename(x).split(args.sep)[:args.num_sep]
    for group_key, group_bigwig_files in groupby(sorted(bigwig_files, key=key_func), key_func):

        group_bigwig_files_list = list(group_bigwig_files)
        logger.info("args sep: {}".format(args.sep))
        logger.info("args num sep: {}".format(args.num_sep))
        logger.info("split filename: {}".format(bigwig_files[0].split(args.sep)[:args.num_sep]))
        logger.info("-----------------------------------------")
        logger.info("processing bigwig files group with key : {}".format(group_key))
        logger.info("comprised of following files: {}".format(group_bigwig_files_list))
        logger.info("-----------------------------------------")

        long_name = os.path.basename(args.sep.join(group_key[:args.num_sep]))
        logger.info("long_name: {}".format(long_name))
        sanitized_long_name = helpers.sanitize(long_name)
        logger.info("sanitized_long_name: {}".format(sanitized_long_name))
        aggregate = AggregateTrack(
            name=sanitized_long_name,
            tracktype='bigWig',
            short_label=sanitized_long_name,
            long_label=sanitized_long_name,
            aggregate='transparentOverlay',
            showSubtrackColorOnUi='on',
            autoScale='on',
            priority='1.4',
            alwaysZero='on',
            visibility="full"
            )
        
        for bigwigfile in group_bigwig_files_list:
            logger.info("--------------------------")
            logger.info("bigwigfile: {}".format(bigwigfile))
            logger.info("--------------------------")
            base_track = os.path.basename(bigwigfile)
            logger.info("Base track: {}".format(base_track))
            sanitized_base_track = helpers.sanitize(base_track)
            logger.info("Sanitized: {}".format(sanitized_base_track))
            
            if "pos" in bigwigfile or "plus" in bigwigfile:
                color = "0,100,0" 
            else:
                color = "100,0,0"
            track = Track(
                name=sanitized_base_track,
                url=os.path.join(URLBASE, GENOME, base_track),
                tracktype="bigWig",
                short_label=sanitized_base_track,
                long_label=sanitized_base_track,
                color=color,
                local_fn=bigwigfile,
                remote_fn=os.path.join(GENOME, base_track)
                )
            logger.info("aggregate.add_subtrack: {}".format(track.name))
            aggregate.add_subtrack(track)
        supertrack.add_tracks(aggregate)

    # process bigbed files as single track
    ######################################

    for bigbed_file in bigbed_files:

        logger.info("--------------------------")
        logger.info("bigbedfile: {}".format(bigbed_file))
        logger.info("--------------------------")

        if "pos" in bigbed_file or "plus" in bigbed_file:
            color = "0,100,0" 
        else:
            color = "100,0,0"
        base_track = os.path.basename(bigbed_file)
        long_name = args.sep.join(base_track.split(args.sep)[:args.num_sep])
        sanitized_long_name = helpers.sanitize(long_name)
        logger.info(f"base_track: {base_track}")
        logger.info(f"long_name: {long_name}")
        logger.info(f"sanitized_long_name: {sanitized_long_name}")
        
        track = Track(
            name=sanitized_long_name,
            url=os.path.join(URLBASE, GENOME, base_track),
            tracktype="bigBed",
            short_label=sanitized_long_name,
            long_label=sanitized_long_name,
            color=color,
            local_fn=bigbed_file,
            remote_fn=os.path.join(GENOME, base_track),
            visibility="dense"
        )
        supertrack.add_tracks(track)

    trackdb.add_tracks(supertrack)
    result = hub.render()
    
    hub.remote_fn = os.path.join(uploaddir, "{}.hub.txt".format(hub_name))

    # process bigbed files  (bam?)
    ######################
    ##  UNUSED
    # if bigwigfile.endswith(".bw") or bigwigfile.endswith('.bigWig'): tracktype = "bigWig"
    # if bigwigfile.endswith(".bb") or bigwigfile.endswith('.bigBed'): tracktype = "bigBed"
    # if bigwigfile.endswith(".bam"):                                  tracktype = "bam"
    
    # 'upolading' (locally)
    ########################
    # for track in trackdb.tracks:
        #print("upload_track(track=" + track.__repr__() + ", host=" + args.serverscp + ", user=" + args.user + "run_local=True")
        #upload_track(track=track, host=args.serverscp, user=args.user)
        # upload_track(track=track, host=args.serverscp, user=args.user, run_s3=args.no_s3)
    #     upload_track(track=track, host=HOST, user=USER, run_local=True)

    #print("upload_hub(hub=" + hub.__repr__() + ", host=" + args.serverscp + ", user=" + args.user + "run_local=True")
    #upload_hub(hub=hub, host=args.serverscp, user=args.user)
    # upload_hub(hub=hub, host=args.serverscp, user=args.user, run_s3=args.no_s3)
    
    logger.info("Uploaddir = {}".format(uploaddir))
    Path(uploaddir).mkdir( parents=True, exist_ok=True )
    upload_hub(hub=hub, host=HOST, remote_dir=uploaddir)
    #
    logger.info("UPLOADDIR: {}".format(uploaddir))
    logger.info("BUCKET: {}".format(uploaddir))
    copy_dir_to_aws(
        src=uploaddir,
        dest=uploaddir,
    )
    print("FINAL URL: {}/{}.hub.txt".format(URLBASE, hub_name))

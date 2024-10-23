#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load films, film information, screens and screenings from the IDFA 2020
website.

Created on Wed Nov  4 20:36:18 2020

@author: maarten
"""

import datetime
import os
import re
from enum import Enum, auto
from typing import Dict
from urllib.parse import urlparse

from Shared.application_tools import ErrorCollector, DebugRecorder, comment, Counter
from Shared.parse_tools import FileKeeper, HtmlPageParser, ScreeningKey, try_parse_festival_sites
from Shared.planner_interface import FestivalData, Screening, Film, FilmInfo, ScreenedFilm, get_screen_from_parse_name
from Shared.web_tools import UrlFile, iri_slug_to_url

FESTIVAL = 'IDFA'
FESTIVAL_CITY = 'Amsterdam'
FESTIVAL_YEAR = 2024

DEBUGGING = True
ALWAYS_DOWNLOAD = False
AUDIENCE_PUBLIC = 'publiek'

# Files.
FILE_KEEPER = FileKeeper(FESTIVAL, FESTIVAL_YEAR)
AZ_PAGE_COUNT = 9

# URL information.
FESTIVAL_HOSTNAME = 'https://festival.idfa.nl'
AZ_PATH = '/collectie/?A_TO_Z_TYPE=Publiek'
SECTION_PATH = '/festivalgids/wegwijzers/'

# Application tools.
ERROR_COLLECTOR = ErrorCollector()
DEBUG_RECORDER = DebugRecorder(FILE_KEEPER.debug_file)
COUNTER = Counter()


def main():
    # Initialize a festival data object.
    comment('Creating festival data object.')
    festival_data = IdfaData(FILE_KEEPER.plandata_dir)

    # Setup counters.
    COUNTER.start('film URLs')
    COUNTER.start('film title')
    COUNTER.start('add film attempts')
    COUNTER.start('combinations')
    COUNTER.start('films')
    COUNTER.start('no description')
    COUNTER.start('meta dicts')
    COUNTER.start('articles')
    COUNTER.start('combination screenings')
    # COUNTER.start('az-counters')
    # COUNTER.start('sections')
    # COUNTER.start('pathways')
    # COUNTER.start('sections with css data')
    # COUNTER.start('corrected urls')
    # COUNTER.start('improper dates')
    # COUNTER.start('improper times')
    # COUNTER.start('filminfo update')
    # COUNTER.start('filminfo extended')

    # Try parsing the websites.
    try_parse_festival_sites(parse_idfa_sites, festival_data, ERROR_COLLECTOR, DEBUG_RECORDER, FESTIVAL, COUNTER)


def parse_idfa_sites(festival_data):
    comment(f'Parsing {FESTIVAL} {FESTIVAL_YEAR} pages.')
    parse_from_hardcoded_urls(festival_data)

    # comment('Trying new AZ pege(s)')
    # load_az_pages(festival_data)
    #
    # comment('Parsing section pages.')
    # get_films_from_section(festival_data)
    #
    # comment('Parsing film pages')
    # FilmDetailsReader(festival_data).get_film_details()

    comment(f'Done parsing {FESTIVAL} {FESTIVAL_YEAR} pages.')
    report_missing_films()


def parse_from_hardcoded_urls(festival_data):
    urls = [
        'https://festival.idfa.nl/film/0b9f2c6b-281c-48f0-9279-945b50956bd4/the-1957-transcripts/',
        'https://festival.idfa.nl/film/0d2c2467-131b-4042-953c-aec0434355f1/2073/',
        'https://festival.idfa.nl/film/24e63236-56f6-4bce-8290-b2c3a05fc86c/7-walks-with-mark-brown/',
        'https://festival.idfa.nl/film/df9b15ab-77d6-47d8-832c-aa5229e278e1/abece/',
        'https://festival.idfa.nl/film/99eb13f5-3f3e-46f5-8220-ddb350467c37/abo-zaabal-89/',
        'https://festival.idfa.nl/film/b4d6cb0b-2333-4311-93df-2a274644d773/about-a-hero/',
        'https://festival.idfa.nl/film/3e33f891-cd12-4a0b-99aa-d66251fd4280/acting/',
        'https://festival.idfa.nl/film/6457a380-c2f3-45ee-a2de-b721aad3da49/agent-of-happiness/',
        'https://festival.idfa.nl/film/85b17b81-476b-4337-bf93-a584663db6ce/all-is-well/',
        'https://festival.idfa.nl/film/60fe7175-fc3a-4790-b1ae-896c03c7dc31/alma-del-desierto/',
        'https://festival.idfa.nl/film/7bc79a6a-2f3c-4510-9117-52f765d3a62e/alternative-3/',
        "https://festival.idfa.nl/film/6015e727-7d0a-40dd-820b-7d5553d63a2d/am-i-the-skinniest-person-you've-ever-seen/",
        'https://festival.idfa.nl/film/9818d2db-5044-4478-9b57-00fba78a1166/an-american-pastoral/',
        'https://festival.idfa.nl/film/233f440e-2c45-4476-b302-dccdbdcbc6ba/apocalypse-in-the-tropics/',
        'https://festival.idfa.nl/film/e9835af9-9d52-4710-b16d-c9afdf5b5166/archipelago-of-earthen-bones-to-bunya/',
        'https://festival.idfa.nl/film/76b681e3-7145-4103-a985-306945f2885c/architecton/',
        'https://festival.idfa.nl/film/dee68be9-5ba6-4ecd-8fc8-f7700783eb61/at-all-kosts/',
        "https://festival.idfa.nl/film/30270ca8-cb92-41bb-a66d-1aa7dab43e11/at-this-moment-in-the-nation's-sky/",
        'https://festival.idfa.nl/film/c3174434-a521-4c60-8bea-f37fa41895e5/averroes-and-rosa-parks/',
        'https://festival.idfa.nl/film/2fe91800-c034-4c7c-8acf-83b51e4c15b9/the-ban/',
        'https://festival.idfa.nl/film/74f99965-ffde-4817-b771-fa53f43912c9/de-bateyes/',
        'https://festival.idfa.nl/film/c272f07a-0245-454a-ade5-2812cc9b756e/the-battle-for-laikipia/',
        'https://festival.idfa.nl/film/945aa541-86fe-434a-beb6-bce6b6516b6a/been-here-stay-here/',
        'https://festival.idfa.nl/film/9c7452fe-3b22-49cd-9207-9344ad36c6de/before-then/',
        'https://festival.idfa.nl/film/c39a09ec-51ba-4c3d-a929-f0e46e7a7d52/being-john-smith/',
        'https://festival.idfa.nl/film/d6ac146f-c253-4169-883f-c40cc80790f8/the-belle-from-gaza/',
        'https://festival.idfa.nl/film/6887aef5-6233-4659-b90d-24f22dbb18ac/best-of-enemies:-buckley-vs.-vidal',
        'https://festival.idfa.nl/composition/54fd3f92-1615-4a38-97e9-f224494beabd/best-of-idfa:-audience-favorites/',
        'https://festival.idfa.nl/composition/91add977-cd3a-4d38-a034-58b9419f0253/best-of-idfa:-award-winners/',
        'https://festival.idfa.nl/film/4ef874f8-a5d1-42d0-944d-3f5a8bf99ab3/bestiaries-herbaria-lapidaries/',

        'https://festival.idfa.nl/film/258beee7-829e-44dc-a9a1-c8a5e8d7cd7e/black-box-diaries/',
        'https://festival.idfa.nl/film/0c0171ff-1144-4b16-9fd8-7fa03973e9d4/black-butterflies/',
        'https://festival.idfa.nl/film/186e272e-e389-4dbc-8e9d-5526b60e1459/black-harvest/',
        'https://festival.idfa.nl/film/9505c39d-b4d0-4ab5-bd2b-746ab17b5be0/blink/',
        'https://festival.idfa.nl/film/9ae62a0a-8cd6-4f5c-b69c-8d5a2bb365d7/bloodline/',
        'https://festival.idfa.nl/film/b8a5538d-9ff3-46a1-831d-37aea274fc41/blowing-in-the-wind/',
        'https://festival.idfa.nl/film/f62f4a5a-7845-44a5-8080-d48325d738c4/blue-orchids/',
        'https://festival.idfa.nl/film/008e3e33-c216-4314-8e59-c87824ec9600/bogancloch/',
        'https://festival.idfa.nl/film/8abb5d29-d7df-42ed-8856-7cdcae2457cb/la-bonita/',
        'https://festival.idfa.nl/film/43b41755-a905-4f2b-a989-81ab7f4f70f3/bright-future/',
        'https://festival.idfa.nl/film/f80f4c1a-0f6e-4918-90ad-d32c4e8e5624/the-brink-of-dreams/',
        'https://festival.idfa.nl/film/c1546275-0b67-4694-bcb9-7385f24c9589/the-building-and-burning-of-a-refugee-camp/',
        'https://festival.idfa.nl/film/835ecb24-42c7-459b-82fe-e63aeb6491ff/the-cats-of-gokogu-shrine/',
        'https://festival.idfa.nl/film/424a7e3c-9e4e-48d4-8b4b-6f14172663cc/chronicles-of-the-absurd/',
        'https://festival.idfa.nl/film/7575e807-d660-400c-b930-1b97c65eb3e0/close-up/',
        'https://festival.idfa.nl/film/be54b7ec-403c-449c-a615-fa79e6d7913d/cohabitants/',
        'https://festival.idfa.nl/film/a042a38b-da83-45cb-aa11-69bd8fd82c42/the-color-of-armenian-land/',
        'https://festival.idfa.nl/film/2cbb2db6-71f5-49d6-9c38-95587d40ff45/the-color-of-pomegranates/',
        'https://festival.idfa.nl/film/6ca5c78a-16d3-4a7d-a6d4-4647fde9cbb3/crushed/',
        'https://festival.idfa.nl/film/125f52cc-1049-44a5-9c4c-c434dd258348/cyclemahesh/',
        'https://festival.idfa.nl/film/6937125c-9c63-4d1c-878f-42e72b1d3c2a/dahomey/',
        'https://festival.idfa.nl/film/01813cfa-1c57-4917-9cb5-6ed5c3ed49eb/the-daughter-of-both-women/',
        'https://festival.idfa.nl/film/0766cda0-7abe-4a79-8c82-14e1d94bbf67/de-cierta-manera/',
        'https://festival.idfa.nl/composition/a5957f3a-f6a2-4299-a8c3-68e30ce6b085/de-groene-amsterdammer-dag/',
        'https://festival.idfa.nl/film/e9e21b0f-4a62-48f0-8f44-d4f4d5823147/dear-beautiful-beloved/',
        'https://festival.idfa.nl/film/82b0cc31-c269-47b1-9154-ceb441947c40/la-despedida/',
        'https://festival.idfa.nl/film/ac51d4e6-7ab3-40e6-8582-70587bd7b771/dial-h-i-s-t-o-r-y/',
        'https://festival.idfa.nl/film/8b1b03ed-ae9c-4a87-9304-7ac9d20530f4/the-diary-of-a-sky/',
        'https://festival.idfa.nl/film/a6b8866e-c52f-4ff0-87b3-622f65ec340f/didy/',
        'https://festival.idfa.nl/film/4df3a796-4a0a-4990-807a-3a1e028c1d67/direct-action/',

        'https://festival.idfa.nl/film/e051c672-c70b-4a63-9d5d-9ec97e846670/double-take/',
        'https://festival.idfa.nl/film/bd163cb1-e013-4e9c-af9c-f4f58882fc92/echoes-within/',
        'https://festival.idfa.nl/film/3c8f64b6-35f1-46d3-8baf-97f2f1db1fcd/edhi-alice/',
        'https://festival.idfa.nl/film/fa558e9b-e981-456c-8e82-1ce4a8b420f7/eight-postcards-from-utopia/',
        'https://festival.idfa.nl/film/18955a7e-f914-44e2-8985-2be142d6fd13/elementary/',
        'https://festival.idfa.nl/film/3c91dcc9-bd5f-4e15-9a57-c86da975eaf4/el-enemigo/',
        'https://festival.idfa.nl/film/daf03150-3b4b-421c-80ca-cde606cc68dc/eno/',
        'https://festival.idfa.nl/film/a964911a-a17c-4881-89ff-7a8f6580fc61/entretierra/',
        'https://festival.idfa.nl/film/56deca66-872d-4967-9e58-2ab917f38796/ernest-cole:-lost-and-found/',
        'https://festival.idfa.nl/film/2006a94e-56a6-4b50-a4e3-635d222534c9/every-day-words-disappear-or-michael-hardt-on-the-politics-of-love/',
        'https://festival.idfa.nl/film/1a0db911-2bbe-4de5-9c6a-ba5de4fbe3c7/everything-will-be-alright/',
        'https://festival.idfa.nl/film/2a3fb5b3-0bcc-4997-a68d-7f42f4161214/eyes-of-gaza/',
        'https://festival.idfa.nl/film/b436f2e1-3698-4468-92ed-e230255f4a25/the-fabulous-gold-harvesting-machine/',
        'https://festival.idfa.nl/film/d3c39f5c-737a-4388-9401-63502c34b345/a-family-portrait-20142024/',
        'https://festival.idfa.nl/film/0a31965b-4a74-400d-83af-840efcb9f6de/a-family/',
        'https://festival.idfa.nl/film/3c6d61bc-df6e-4da5-8a30-0b4a2af5318d/farming-the-revolution/',
        'https://festival.idfa.nl/film/bbeeb109-5ee7-4bd3-b5be-557a7eb94091/favoriten/',
        'https://festival.idfa.nl/film/ec691004-8c2b-472e-a10e-4f306f354483/the-fen-fire/',
        'https://festival.idfa.nl/film/3439d8a6-0dfb-4e6e-a138-7030758eb29f/a-fidai-film/',
        'https://festival.idfa.nl/film/96cd0d27-15b7-4ba5-9478-ff4dc3692a88/the-flats/',
        'https://festival.idfa.nl/film/beb04801-634d-47a4-a08b-5bedcc49bb92/the-flower-by-the-road/',
        'https://festival.idfa.nl/film/f7783cce-7b95-44df-af1c-ee5eb576d737/the-flowers-stand-silently-witnessing/',
        'https://festival.idfa.nl/film/b0506a68-e0a0-467a-b336-982ed864d7f1/flying-anne/',
        'https://festival.idfa.nl/film/4fb06a48-cf8a-4b90-b26d-3159cdda9e25/a-frown-gone-mad/',
        'https://festival.idfa.nl/film/8afa581b-9a08-4ab0-9c45-e2ff50271cb1/garanti-100percent-kreol/',
        'https://festival.idfa.nl/film/5c677635-0bdd-4d00-b06a-40dc0aec0c02/the-golden-age/',
        'https://festival.idfa.nl/film/9966b494-1e17-47bf-b74f-9cd7bf8f96e6/grand-theft-hamlet/',
        'https://festival.idfa.nl/film/3d9b86bb-ddb2-46f8-baba-f21ef13f0aec/the-great-wall/',
        'https://festival.idfa.nl/film/0da6ec00-47ba-4aa3-8d98-778939a8627f/green-is-the-new-red/',
        'https://festival.idfa.nl/film/3f5005c9-982d-494a-ba55-a1b1686149ee/guanabacoa:-cronicas-de-mi-familia/',

        'https://festival.idfa.nl/composition/7e8208bb-1bff-4ab1-9bfa-45541cabd43b/guest-of-honor-talk:-johan-grimonprez/',
        'https://festival.idfa.nl/film/41ef1c66-680d-43ba-a54c-f02eec61b848/the-guest/',
        'https://festival.idfa.nl/film/64aadff8-0e08-4bde-b83b-4c89aa4ac490/hard-to-break/',
        'https://festival.idfa.nl/film/8d47decb-e540-47b7-8ec9-16ad3bec3955/hey-dad/',
        'https://festival.idfa.nl/film/bd07d842-74f3-454f-8570-70f1c3f167e3/higher-than-acidic-clouds/',
        "https://festival.idfa.nl/film/9261e79c-197c-4e08-9e72-bfb24b289c06/hitchcock-didn't-have-a-belly-button:-karen-black-interview-by-johan-grimonprez/",
        'https://festival.idfa.nl/film/18307763-1930-4160-bde1-75904ed595c0/home-game/',
        'https://festival.idfa.nl/film/d4acb61c-553e-4f69-8bb5-414ee46c0742/how-to-suture-the-soil/',
        'https://festival.idfa.nl/film/753db578-75a7-4ad8-99b7-304b95103fd7/huaquero/',
        'https://festival.idfa.nl/composition/78658a37-a2f5-4c3f-bde8-77f55f0ae560/idfa-junior/',
        'https://festival.idfa.nl/film/dc9abf27-10ef-436f-9e18-806ecfdec347/in-the-open/',
        'https://festival.idfa.nl/film/3c997740-7de5-453d-b82d-52b8242af33e/indicios-del-inscrito/',
        'https://festival.idfa.nl/film/a59ba580-8fce-492f-9290-44fc8e82b109/infiltrators/',
        'https://festival.idfa.nl/film/c2c42516-c045-4e27-883e-ade0a7f6c89c/intercepted/',
        'https://festival.idfa.nl/film/17c4d733-6828-4d41-9f39-0c957f41d1ce/the-invasion/',
        'https://festival.idfa.nl/film/1275d5f7-d6f3-4f69-b20d-e9aa4d1c59e7/the-invisible-ones/',
        'https://festival.idfa.nl/film/205ab1c5-9920-4f27-87ef-83ce4b41b4a6/iron/',
        'https://festival.idfa.nl/film/107b2ef4-78c4-4c7c-816a-07f2a8155903/ire-a-santiago/',
        'https://festival.idfa.nl/film/54c125be-df8c-4086-8c97-adb6fd45fa17/isla-del-tesoro/',
        'https://festival.idfa.nl/film/f0fe0304-ce5b-4f8a-83a1-0400fa8cd06c/una-isla-para-miguel/',
        'https://festival.idfa.nl/film/d8cccf65-b096-492c-a316-e46ede6b142a/isla/',
        "https://festival.idfa.nl/film/0df43c61-9f24-48cb-9a5e-d7c38d2a9d76/i'm-not-everything-i-want-to-be/",
        'https://festival.idfa.nl/film/53888119-0676-44d8-ba73-63c03d064895/the-jacket/',
        'https://festival.idfa.nl/film/dfa76e91-c374-402a-a4d9-92d912f990e1/jakub/',
        'https://festival.idfa.nl/film/4c79af2f-cf99-4371-b862-992d527e7a1a/k-family-affairs/',
        'https://festival.idfa.nl/film/daee4574-d7d0-448c-85c2-32a41d93733f/lanawaru/',
        'https://festival.idfa.nl/film/1a333974-fbe1-468c-8d59-d9ef2b946da8/the-landscape-and-the-fury/',
        'https://festival.idfa.nl/film/3faa33b5-e3db-4eda-bbd1-88d315b64fd3/the-last-expedition/',
        'https://festival.idfa.nl/film/4c52c5dd-f3bc-4ce1-aef4-1959fd55577c/lie-to-me/',
        'https://festival.idfa.nl/film/4d7140b0-7b6f-4a06-afb5-465bc9592ba0/life-and-other-problems/',

        'https://festival.idfa.nl/film/a435e732-1898-4013-857a-9fbfc24abe53/lift-lady/',
        'https://festival.idfa.nl/film/db6db054-4505-4e68-bd75-81c0a92b1e98/light-memories/',
        'https://festival.idfa.nl/film/d0654d1c-8ed5-4092-87d9-469d631d7ff7/light-of-the-setting-sun/',
        'https://festival.idfa.nl/film/19b88fef-e87b-44fc-912f-870f2ee97ae2/like-the-glitch-of-a-ghost/',
        'https://festival.idfa.nl/film/c84a16d6-7422-413a-8ad5-f25fd95b2ea4/loss-adjustment/',
        'https://festival.idfa.nl/film/f58ead66-fdc7-4b1c-a058-3fe6a7e99932/machine-boys/',
        'https://festival.idfa.nl/film/05420db8-3df3-46c7-92da-7749d4893ec3/make-it-look-real/',
        'https://festival.idfa.nl/film/55f8d8c8-5981-4818-8f9a-ecc33334c43a/mama-micra/',
        'https://festival.idfa.nl/film/eb97021c-bcf6-4588-9c01-c7e2b1805e33/man-number-4/',
        'https://festival.idfa.nl/film/5afa2b67-d48f-47f8-a7c1-38094dd69430/el-mar-la-mar/',
        'https://festival.idfa.nl/film/624850b5-37fa-4930-9734-e75424ccd41b/mi-aporte/',
        'https://festival.idfa.nl/film/1b88b368-f1a2-49b1-b4ff-5a0fd8f65e5a/milk/',
        'https://festival.idfa.nl/film/718d7dfc-0e80-486a-a9b8-7a213efa6fca/missing-rio-doce/',
        'https://festival.idfa.nl/film/848b3a01-7ea9-424c-a950-536ccb220923/misty-man/',
        'https://festival.idfa.nl/film/6e37bd50-028a-4b8b-9e41-e339b3eb8299/moore-for-sale/',
        'https://festival.idfa.nl/film/31691c79-ea8a-4a21-abae-d8f9328504f8/a-move/',
        'https://festival.idfa.nl/film/9ef8a1af-a795-4c26-a9ac-db4dd6fbd6a8/mutts/',
        'https://festival.idfa.nl/film/1d7a4328-9139-4595-b486-ffc04295fd56/my-homeland/',
        'https://festival.idfa.nl/film/4304edde-f3a0-4d2b-be54-6ec51392e41c/my-sextortion-diary/',
        'https://festival.idfa.nl/film/451f41f9-3ec3-4f40-bc3b-f0ec309ae69c/my-stolen-planet/',
        'https://festival.idfa.nl/film/9aaf2c69-6f7f-4606-9813-e05181c3a34b/neshoma/',
        'https://festival.idfa.nl/film/3c5d414f-a8bf-4c89-a9fa-bfa20274b599/the-nights-still-smell-of-gunpowder/',
        'https://festival.idfa.nl/film/0035141e-489a-4b6c-8217-2e07846dcd21/los-ninos-lobo/',
        'https://festival.idfa.nl/film/e73f676c-f15b-40e7-b8b1-e3e4142e98e8/no-other-land/',
        'https://festival.idfa.nl/film/23f034e9-bce7-4ed5-9333-2bfd26e48842/noise:-unwanted-sound/',
        'https://festival.idfa.nl/composition/5ae7b3e0-c924-4dff-89ef-7637b1f80a75/npo-doc-idfa-audience-award-winner/',
        'https://festival.idfa.nl/film/d8379c96-8271-46ad-912e-ad231fda91c7/off-frame-aka-revolution-until-victory/',
        'https://festival.idfa.nl/film/ed3f3bcb-26a3-4d4b-94bf-bdbcef72d12d/on-the-battlefield/',
        'https://festival.idfa.nl/film/586e88c3-14ef-4d0b-aba3-c0079ea7357e/on-the-border/',
        'https://festival.idfa.nl/film/2fadc85c-ff10-4d56-8b81-f8f21ca8ca9d/once-upon-a-time-in-a-forest/',

        'https://festival.idfa.nl/film/701fad3e-becf-41ff-a69a-0efe6ceed517/one-to-one:-john-and-yoko/',
        'https://festival.idfa.nl/film/63f1223f-7af5-40a4-afd0-1e42dda78eb0/the-other-side-of-the-mountain/',
        'https://festival.idfa.nl/film/9d9eed98-a7cc-4628-b59d-296e693a2d14/paci/',
        'https://festival.idfa.nl/film/f8449344-d64b-4094-a7c8-aa0111ac780c/paradise/',
        'https://festival.idfa.nl/film/78b6079c-139c-438b-82a7-7fd6962a6873/parajanov:-the-last-spring/',
        'https://festival.idfa.nl/film/2f4315c3-b4cc-458d-9611-7ab4da2718a1/park/',
        'https://festival.idfa.nl/film/0a62d3f3-4f03-4bf7-815b-cadbcf42df4b/perfectly-a-strangeness/',
        'https://festival.idfa.nl/film/3ee8cfe5-4b6e-4dde-b50b-a7f1252b0332/personale/',
        'https://festival.idfa.nl/film/ebec7794-c41c-439e-91a1-db6c8e126684/pictures-in-mind/',
        'https://festival.idfa.nl/film/db448332-27d5-4022-8d37-56bfa968d24d/a-place-to-call-home/',
        'https://festival.idfa.nl/film/2760bbce-4536-492a-9d5a-50257ff1863b/planktonium-live/',
        'https://festival.idfa.nl/film/256c8c61-c652-4a90-a250-bb4c1bd331e1/please-step-aside!/',
        'https://festival.idfa.nl/film/4860ffc3-8477-4ed7-9bf9-c5f9b76476c7/the-propagandist/',
        'https://festival.idfa.nl/film/44dc51d2-de03-4937-a32a-7fe2a9a4ef29/raymond-tallis-or-on-tickling/',
        'https://festival.idfa.nl/film/84d7a3fe-6ef1-4c5f-8901-bb648243a429/real/',
        'https://festival.idfa.nl/film/8fc77b65-b299-4475-bb57-f01d2a6da68f/real/',
        'https://festival.idfa.nl/film/2829a6fb-540e-41b5-b8e8-6589a5d9f530/reas/',
        'https://festival.idfa.nl/film/f3541ca3-5c05-4e7d-8170-91cfd4f4e228/red-armypflp:-declaration-of-world-war/',
        'https://festival.idfa.nl/film/5fe8569c-dd36-4b82-b3bc-18a85acada90/respite/',
        'https://festival.idfa.nl/film/e449f173-ca0e-4f85-bc60-fa6aeae28b09/revolving-rounds/',
        'https://festival.idfa.nl/film/a6d565cd-fbb3-4967-937a-7da4880981cc/riefenstahl/',
        'https://festival.idfa.nl/film/48e71ebd-faea-45b0-a34c-c558228b01d6/rising-up-at-night/',
        'https://festival.idfa.nl/film/5dd07a32-2c0d-40c5-9e23-d893d835a154/route-181-fragments-of-a-journey-in-palestine-israel/',
        'https://festival.idfa.nl/film/af17ecfc-dd1c-4ccf-af34-4ea0d9e22288/rule-of-stone/',
        'https://festival.idfa.nl/film/b67e5183-d3a5-4d54-bcb4-737a74ce8d4c/sabbath-queen/',
        'https://festival.idfa.nl/film/2b73f5cd-ba22-46cf-b37d-b7ea8e8329a9/save-our-souls/',
        'https://festival.idfa.nl/film/91f2c6b6-e537-4292-9d82-4f59e68719b1/the-shadow-scholars/',
        'https://festival.idfa.nl/film/abb86475-2e87-4cf7-a0e4-666fbe6043f9/shadow-world/',
        'https://festival.idfa.nl/film/1be33081-a77c-48f2-89c5-2afddf35fd9c/the-shepherd-and-the-bear/',
        'https://festival.idfa.nl/film/d2d33aab-50dc-4ee3-ae4e-bc9bd621a27d/shot-the-voice-of-freedom/',

        'https://festival.idfa.nl/film/cec93ba9-1815-4b0c-9578-1791eb172c51/si-no-puedo-bailar-esta-no-es-mi-revolucion/',
        'https://festival.idfa.nl/film/79dc305e-3887-4916-aed2-86a1fa0197d1/silent-observers/',
        'https://festival.idfa.nl/film/f7c27bde-65af-4b56-abe4-76b06bf0f6c8/simply-divine/',
        "https://festival.idfa.nl/film/663814a5-a22d-4ad6-a1ff-3c29da443f13/a-sisters'-tale/",
        'https://festival.idfa.nl/film/80fac2b6-d775-4b88-8219-14bc5a84d27b/sleep-2/',
        'https://festival.idfa.nl/film/5b7b7670-1269-4677-aea4-13415302deeb/sobre-horas-extras-y-trabajo-voluntario/',
        'https://festival.idfa.nl/film/fb6210b6-9bb3-4be9-811f-442d89ee4308/somewhere-to-be/',
        'https://festival.idfa.nl/film/105d350f-f14a-4efa-b394-7d242a8f7400/songs-of-slow-burning-earth/',
        "https://festival.idfa.nl/film/1795ea9b-959a-4645-bb67-51263d531e71/soundtrack-to-a-coup-d'etat/",
        'https://festival.idfa.nl/film/5fc8b80c-1597-452a-b994-fb09eaaa1500/space-is-the-place/',
        'https://festival.idfa.nl/film/41c1ba79-e31b-4ed8-bf55-737642bb5af0/spiritual-voices/',
        'https://festival.idfa.nl/film/4419de78-3e27-44c0-8e8d-7f741a3da93f/starfilm/',
        'https://festival.idfa.nl/film/27cab503-6a5b-42d0-b44f-a3180f98400e/state-of-silence/',
        'https://festival.idfa.nl/film/402a0440-2b3d-4be1-ad44-cb27ebbf42e2/a-strange-colour-of-dream/',
        'https://festival.idfa.nl/film/ee7a2525-a79d-4d7b-b959-408f2843efc3/sudan-remember-us/',
        'https://festival.idfa.nl/film/e00933f0-9b3e-42b8-a215-1100a928b8de/a-sudden-glimpse-to-deeper-things/',
        'https://festival.idfa.nl/film/4113b729-dc3d-4b14-9346-f79b5f05107d/sugarcane/',
        'https://festival.idfa.nl/film/92a0b86e-79e1-4577-aa77-137606c5753f/sympathy-for-the-devil/',
        'https://festival.idfa.nl/film/574972a0-d954-4b44-9fb4-7823b3dea9be/teaches-of-peaches/',
        'https://festival.idfa.nl/film/3acaa80f-8955-4ebd-b23e-a9b2e9e85d6b/there-are-so-many-things-still-to-say/',
        'https://festival.idfa.nl/film/1f5ee710-34f4-4faf-af66-0b814e0fd1de/theremin:-an-electronic-odyssey/',
        'https://festival.idfa.nl/film/22291dc1-1686-46f0-bdb9-76edc100bb77/things-that-happen-on-earth/',
        'https://festival.idfa.nl/film/25daa142-bcad-4d20-9c20-81918cacbd8b/this-is-(not)-your-ocean/',
        'https://festival.idfa.nl/film/70243ddb-4d50-497f-ac6c-431c73630d13/to-be-continued.-teenhood.',
        'https://festival.idfa.nl/film/33b21750-52dd-42e1-a802-3e60e278d240/tokkotai-paqueta/',
        'https://festival.idfa.nl/film/74bada8d-eabd-4c5a-ae5e-701da581aa2b/toroboro:-the-name-of-the-plants/',
        'https://festival.idfa.nl/film/9e15c3eb-eda2-4687-986b-5fa3a02328fc/tough-love/',
        'https://festival.idfa.nl/film/bdbcdb2f-f218-42f6-95d7-a6d69398be58/trains/',
        'https://festival.idfa.nl/film/03eb86d9-51ec-427b-a4a4-277c1eaefcc9/trans-memoria/',
        'https://festival.idfa.nl/film/cc4d37f6-4c24-4c06-bce5-4e156da508a4/tripoli-a-tale-of-three-cities/',

        'https://festival.idfa.nl/composition/9559ce40-ab75-4913-a4b9-35b6dd5599c8/de-volkskrantdag/',
        'https://festival.idfa.nl/film/69f3cc5d-49aa-476c-a617-212c0e13e8be/the-tunes/',
        'https://festival.idfa.nl/film/203203fd-fbb3-4602-900c-73194975bebd/two-strangers-trying-not-to-kill-each-other/',
        'https://festival.idfa.nl/film/ad70c091-e8dc-49c0-a018-f53203a0c010/two-travellers-to-a-river/',
        'https://festival.idfa.nl/film/033e00df-ca8d-4ee2-ae87-315a664dc6ff/twst-things-we-said-today/',
        'https://festival.idfa.nl/film/be4b91be-b3db-4c2a-875d-2bb2edfa6b08/the-typewriter-and-other-headaches/',
        'https://festival.idfa.nl/film/aabbda73-1018-47b3-8a14-2794605db571/undercover:-exposing-the-far-right/',
        'https://festival.idfa.nl/film/d8904621-13fe-4747-b891-ac82e109702b/union/',
        'https://festival.idfa.nl/film/5bf1f618-e448-4888-a013-989505a6c780/until-the-orchid-blooms/',
        'https://festival.idfa.nl/film/082098d2-0ac1-4b58-975a-d2f11e8a49b5/unwritten-letter/',
        'https://festival.idfa.nl/film/ff3406d1-4405-4e46-a632-294eddb9e512/valentina-and-the-muosters/',
        'https://festival.idfa.nl/film/c7d04a4f-1cc7-4080-b3fb-eb0776b000e1/los-viejos-heraldos/',
        'https://festival.idfa.nl/composition/a2d52329-d5a2-42a3-89ff-ea5ad568be13/vpro-preview/',
        'https://festival.idfa.nl/composition/911f0167-cfc4-4e88-9f29-e8fa48197977/vpro-review/',
        'https://festival.idfa.nl/film/2ee88f11-89af-43ab-8c8f-d44517821bdf/a-want-in-her/',
        'https://festival.idfa.nl/film/c3e84fd1-12f6-43f8-848d-fda1dacfcf23/war-game/',
        'https://festival.idfa.nl/film/00547c35-a59f-4f89-ac40-695a081b2b2d/the-water-eyed-boy/',
        'https://festival.idfa.nl/film/f1e6ac16-548e-4233-89f4-48c169851c27/ways-to-traverse-a-territory/',
        'https://festival.idfa.nl/film/8a8d8f2f-1487-479b-8da4-a91f360401c2/we-are-inside/',
        'https://festival.idfa.nl/film/5b5062ab-c85d-4bf8-bf5d-edab40fe7526/what-i-will/',
        "https://festival.idfa.nl/film/8a5925e6-857e-4ffd-b631-b20ce247cf95/what's-the-film-about/",
        'https://festival.idfa.nl/film/dca690a3-5cef-40e2-b4dc-c0f549a2aa67/when-the-body-says-yes/',
        'https://festival.idfa.nl/film/f4536b60-7b01-472e-bf3a-ee4ee34862b1/where-dragons-live/',
        'https://festival.idfa.nl/film/707b3aaa-3b86-4201-8f8d-120851a8f0fe/a-while-at-the-border/',
        'https://festival.idfa.nl/film/79afc4ea-bafb-450f-98eb-1d126892db11/the-white-house-effect/',
        'https://festival.idfa.nl/film/7b5c5a1e-ef96-4baf-b3f6-f8281e953f12/whoever-deserves-it-will-be-immortal/',
        'https://festival.idfa.nl/film/05b6eba9-17f7-4dbc-ad0e-da92959d72cd/with-grace/',
        'https://festival.idfa.nl/film/7b181c1b-9f46-4c1c-8f3e-113f5d75103c/the-wolves-always-come-at-night/',
        'https://festival.idfa.nl/film/1e79545e-e87b-4ec3-816a-5050ff30a225/would-you-have-sex-with-an-arab/',
        'https://festival.idfa.nl/film/9569acc3-81e7-4963-8b64-baa924023fe1/writing-hawa/',

        'https://festival.idfa.nl/film/d3f8dba9-a4c3-4d14-b612-e3a3f0624221/el-arbol/',
        'https://festival.idfa.nl/film/6e41966f-dc6d-4662-ba5f-8ed0105c99ae/y...-tenemos-sabor',
        'https://festival.idfa.nl/film/081732e1-22a2-46d4-9a7f-1d009baefada/yalla-baba!/',
        'https://festival.idfa.nl/film/eacf78a2-a1ab-4014-9cc2-587f471dc85c/yintah/',
        'https://festival.idfa.nl/film/f53881c0-dd92-4d16-9e67-60ef24108f9d/you-are-the-truck-and-i-am-the-deer/',
    ]
    get_films(festival_data, urls)


def report_missing_films():
    for url, title in FilmEnumeratedPageParser.missing_film_by_url.items():
        print(f'Not added: {title} ({url})')


def load_az_pages(festival_data):
    az_url_base = FESTIVAL_HOSTNAME + AZ_PATH
    for page_number in range(1, AZ_PAGE_COUNT + 1):
        debug_file = os.path.join(os.path.dirname(FILE_KEEPER.debug_file), f'debug_{page_number:02d}.txt')
        debugger = DebugRecorder(debug_file)
        az_file = FILE_KEEPER.az_file(page_number)
        az_url = az_url_base + f'&page={page_number}'
        url_file = UrlFile(az_url, az_file, ERROR_COLLECTOR, debugger)
        az_html = url_file.get_text(comment_at_download='Downloading AZ page.', always_download=ALWAYS_DOWNLOAD)
        if az_html:
            comment(f'Downloaded AZ page #{page_number}, encoding={url_file.encoding}, bytes={len(az_html)}')
            AzPageParser(festival_data, debugger).feed(az_html)
        debugger.write_debug()


def get_films(festival_data, urls):
    for i, url in enumerate(urls):
        COUNTER.increase('film URLs')
        film_file = os.path.join(FILE_KEEPER.webdata_dir, f'enumerated_film_page_{i:03d}.html')
        url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        comment_at_download = f'Downloading enumerated film page #{i}'
        film_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=comment_at_download)
        if film_html:
            FilmEnumeratedPageParser(festival_data, url).feed(film_html)


def get_films_from_section(festival_data):
    section_url = FESTIVAL_HOSTNAME + SECTION_PATH
    section_file = os.path.join(FILE_KEEPER.webdata_dir, 'sections.html')
    url_file = UrlFile(section_url, section_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
    section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD, comment_at_download=f'Downloading {section_url}')
    if section_html:
        comment(f'Analysing sections page, encoding={url_file.encoding}')
        SectionsPageParser(festival_data).feed(section_html)


def get_films_by_section(festival_data, section_urls):
    for i, section_url in enumerate(section_urls):
        section_file = FILE_KEEPER.numbered_webdata_file('section', i)
        url_file = UrlFile(section_url, section_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
        section_html = url_file.get_text(always_download=ALWAYS_DOWNLOAD,
                                         comment_at_download=f'Downloading {section_url}')
        if section_html:
            comment(f'Analysing section page, encoding={url_file.encoding}')
            FilmsFromSectionPageParser(festival_data, section_url).feed(section_html)


class FilmEnumeratedPageParser(HtmlPageParser):
    class FilmParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        AFTER_TITLE = auto()
        AWAITING_COMBINATION = auto()
        IN_DESCRIPTION = auto()
        AWAITING_METADATA = auto()
        IN_METADATA = auto()
        IN_METADATA_ITEM = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        IN_PARAGRAPH = auto()
        IN_STYLE = auto()
        DONE = auto()

    missing_film_by_url = {}
    category_key_by_subdir = {
        'film': 'films',
        'composition': 'combinations',
    }

    def __init__(self, festival_data, url):
        HtmlPageParser.__init__(self, festival_data, DEBUG_RECORDER, 'F', debugging=DEBUGGING)
        self.film = None
        self.url = url
        self.article = None
        self.title = None
        self.metadata_label = None
        self.film_property_by_label = {}
        self.medium_category = None
        self.subsection = None
        self.sorting_from_site = False

        # Draw a bar with the url.
        self.print_debug(self.bar, f'Analysing film URL {self.url}')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)

    def set_title(self, attr_value):
        self.title = attr_value
        COUNTER.increase('film title')

    def get_subsection_from_sections(self):
        url = FESTIVAL_HOSTNAME + SECTION_PATH

        sections = []
        try:
            sections_str = self.film_property_by_label['sections']
        except KeyError:
            sections_str = None

        if sections_str:
            sections = sections_str.strip("'").split(', ')

        subsection_name = sections[-1] if sections else None
        try:
            subsection = self.festival_data.subsection_by_name[subsection_name]
        except KeyError:
            section = self.festival_data.get_section(subsection_name, color='azure')
            subsection = self.festival_data.get_subsection(subsection_name, url, section)

        return subsection

    def add_film(self):
        # Create a new film.
        COUNTER.increase('add film attempts')
        self.film = self.festival_data.create_film(self.title, self.url)
        if self.film is None:
            ERROR_COLLECTOR.add(f'Could not create film:', f'{self.title} ({self.url})')
        else:
            # Fill medium category.
            self.film.subsection = None
            category_subdir = self.url.split('/')[3]
            self.film.medium_category = self.category_key_by_subdir[category_subdir]

            # Fill duration.
            if self.film.medium_category == 'films':
                minutes = int(self.film_property_by_label['length'].split()[0])     # 207 min
                COUNTER.increase('films')
            else:
                minutes = 0
                COUNTER.increase('combinations')
            self.film.duration = datetime.timedelta(minutes=minutes)

            # Get subsection.
            self.film.subsection = self.get_subsection_from_sections()

            # Add the film to the list.
            self.festival_data.films.append(self.film)

    def add_film_info(self):
        descr_threshold = 256

        # Construct description.
        self.description = (self.description or self.article or '')
        self.description or COUNTER.increase('no description')
        self.article = self.article or self.description
        if len(self.description) > descr_threshold:
            self.description = self.description[:descr_threshold] + '…'
        if self.article:
            COUNTER.increase('articles')
        else:
            self.article = ''

        # Set metadata.
        metadata = self.film_property_by_label
        if metadata:
            COUNTER.increase('meta dicts')

        # Add film info.
        film_info = FilmInfo(self.film.film_id, self.description, self.article, metadata=metadata)
        self.festival_data.filminfos.append(film_info)

    def set_metadata_item(self, data):
        self.film_property_by_label[self.metadata_label] = data

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)
        state = self.FilmParseState

        match [self.state_stack.state(), tag, attrs]:
            case [state.IDLE, 'title', _]:
                self.state_stack.push(state.AWAITING_TITLE)
            case [state.AWAITING_TITLE, 'img', a] if a[0][0] == 'alt':
                self.set_title(attrs[0][1])
                self.state_stack.change(state.AFTER_TITLE)
            case [state.AFTER_TITLE, 'div', a] if a[0] == ('variant', '3'):
                self.state_stack.change(state.AWAITING_COMBINATION)
            case [state.AWAITING_COMBINATION, 'div', _]:
                self.state_stack.change(state.IN_DESCRIPTION)
            case [state.AFTER_TITLE | state.IN_METADATA, 'div', a] if a and a[0][0] == 'data-meta':
                self.metadata_label = a[0][1]
                self.state_stack.change(state.IN_METADATA)
                self.state_stack.push(state.IN_METADATA_ITEM)
            case [state.IDLE, 'p', a] if a and a[0] == ('index', '0'):
                self.state_stack.push(state.IN_ARTICLE)
                self.state_stack.push(state.IN_PARAGRAPH)
            case [state.IN_ARTICLE, 'p', _]:
                self.state_stack.push(state.IN_PARAGRAPH)
            case [state.IN_PARAGRAPH, 'style', _]:
                self.state_stack.push(state.IN_STYLE)
            case [state.IDLE, 'footer', _]:
                self.add_film()
                self.add_film_info()
                self.state_stack.change(state.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        match [self.state_stack.state(), tag]:
            case [self.FilmParseState.IN_STYLE, 'style']:
                self.state_stack.pop()
            case [self.FilmParseState.IN_PARAGRAPH, 'p']:
                if not self.article_paragraphs:
                    self.description = self.article_paragraph
                self.add_paragraph()
                self.state_stack.pop()
            case [self.FilmParseState.IN_ARTICLE, 'div']:
                self.set_article()
                self.state_stack.pop()
            case [self.FilmParseState.IN_METADATA_ITEM, 'div']:
                self.state_stack.pop()
            case [self.FilmParseState.IN_METADATA, 'div']:
                self.state_stack.pop()
            case [state, 'footer'] if state != self.FilmParseState.DONE:
                self.missing_film_by_url[self.url] = self.title

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        match self.state_stack.state():
            case self.FilmParseState.IN_DESCRIPTION:
                self.description = data
                self.state_stack.pop()
            case self.FilmParseState.IN_METADATA_ITEM:
                self.set_metadata_item(data)
            case self.FilmParseState.IN_PARAGRAPH:
                self.article_paragraph += data


class AzPageParser(HtmlPageParser):
    class AzParseState(Enum):
        IDLE = auto()
        IN_ARTICLE = auto()

    def __init__(self, festival_data, debugger=None):
        HtmlPageParser.__init__(self, festival_data, debugger or DEBUG_RECORDER, 'AZ', debugging=DEBUGGING)
        self.sorting_from_site = False
        self.film = None
        self.state_stack = self.StateStack(self.print_debug, self.AzParseState.IDLE)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.AzParseState.IDLE) and tag == 'article':
            self.state_stack.push(self.AzParseState.IN_ARTICLE)
            COUNTER.increase('az-counters')

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.AzParseState.IN_ARTICLE) and tag == 'article':
            self.state_stack.pop()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)


class FilmDetailsReader:
    def __init__(self, festival_data):
        self.festival_data = festival_data

    def get_film_details(self):
        always_download = ALWAYS_DOWNLOAD
        for film, sections in FilmsFromSectionPageParser.sections_by_film.items():
            comment(f'Parsing film details of {film.title}')
            film_file = FILE_KEEPER.film_webdata_file(film.film_id)
            url = film.url
            url_file = UrlFile(url, film_file, ERROR_COLLECTOR, DEBUG_RECORDER, byte_count=200)
            film_html = url_file.get_text(always_download=always_download,
                                          comment_at_download=f'Downloading {film.url}')
            if film_html:
                print(f'Analysing film page, encoding={url_file.encoding}')
                corrected_url = None if url == film.url else url
                FilmPageParser(self.festival_data, film, sections, corrected_url=corrected_url).feed(film_html)


class SectionsPageParser(HtmlPageParser):
    class SectionParseState(Enum):
        AWAITING_URL = auto()
        DONE = auto()

    def __init__(self, festival_date):
        super().__init__(festival_date, DEBUG_RECORDER, 'S', debugging=DEBUGGING)
        self.section_urls = []
        self.pathway_urls = []
        self.state_stack = self.StateStack(self.print_debug, self.SectionParseState.AWAITING_URL)

    def add_section(self, url):
        self.section_urls.append(url)
        COUNTER.increase('sections')

    def add_pathway(self, url):
        self.pathway_urls.append(url)
        COUNTER.increase('pathways')

    def add_theme(self, slug):
        url = iri_slug_to_url(FESTIVAL_HOSTNAME, slug)
        theme = slug.split('/')[1]
        if theme == 'section':
            self.add_section(url)
        elif theme == 'pathways':
            self.add_pathway(url)
        else:
            ERROR_COLLECTOR.add('Unexpected theme', f'{theme}')

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.SectionParseState.AWAITING_URL):
            if tag == 'a':
                if len(attrs) == 2 and attrs[0][0] == 'class' and attrs[0][1] == 'css-avil9w' and attrs[1][0] == 'href':
                    self.add_theme(attrs[1][1])
            elif tag == 'footer':
                self.state_stack.change(self.SectionParseState.DONE)
                get_films_by_section(self.festival_data, self.section_urls)


class FilmsFromSectionPageParser(HtmlPageParser):
    class FilmsParseState(Enum):
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_DESCR = auto()
        IN_DESCR = auto()
        AWAITING_FILM_URL = auto()
        IN_FILM_URL = auto()
        AWAITING_FILM_TITLE = auto()
        IN_FILM_TITLE = auto()
        IN_FILM_PROPERTIES = auto()
        IN_FILM_PROPERTY = auto()
        DONE = auto()

    color_by_section_id = {
        1: 'DodgerBlue',
        2: 'PeachPuff',
        3: 'PeachPuff',
        4: 'DodgerBlue',
        5: 'PaleVioletRed',
        6: 'LightSalmon',
        7: 'HotPink',
        8: 'Khaki',
        9: 'SpringGreen',
        10: 'DarkSeaGreen',
        11: 'OliveDrab',
        12: 'Olive',
        13: 'SpringGreen',
        14: 'PeachPuff',
        15: 'DodgerBlue',
        16: 'PeachPuff',
        17: 'DarkMagenta',
        18: 'IndianRed',
        19: 'PaleVioletRed',
        20: 'SpringGreen',
        21: 'CadetBlue',
        22: 'PapayaWhip',
        23: 'Orchid',
        24: 'DarkSeaGreen',
        25: 'PaleVioletRed',
        26: 'PeachPuff',
        27: 'PapayaWhip',
    }
    sections_by_film = {}

    def __init__(self, festival_data, section_url):
        super().__init__(festival_data, DEBUG_RECORDER, 'FS', debugging=DEBUGGING)
        self.section_url = section_url
        self.section_name = None
        self.subsection = None

        # Initialize film data.
        self.film_url = None
        self.film_title = None
        self.film = None
        self.film_duration = None
        self.film_property_by_label = None
        self.metadata_key = None
        self.init_film_data()

        # Draw a bar with section info.
        self.draw_headed_bar(section_url)

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmsParseState.AWAITING_TITLE)

    def init_film_data(self):
        self.film_url = None
        self.film_title = None
        self.film = None
        self.film_duration = None
        self.film_property_by_label = {}
        self.metadata_key = None

    def reset_film_parsing(self):
        self.state_stack.pop()
        self.set_duration()
        self.add_film()
        self.init_film_data()

    def draw_headed_bar(self, section_url):
        url_obj = urlparse(section_url)
        url_parts = url_obj.path.split('/')
        theme_type = url_parts[1]
        slug = url_parts[3]
        print(f'{theme_type} {self.headed_bar(header=slug)}')
        self.print_debug(self.headed_bar(header=slug))

    def get_subsection(self, section_description=None):
        if self.section_name:
            section = self.festival_data.get_section(self.section_name)
            try:
                section.color = self.color_by_section_id[section.section_id]
            except KeyError as e:
                ERROR_COLLECTOR.add(e, f'No color for section {section.name}')
            subsection = self.festival_data.get_subsection(section.name, self.section_url, section)
            subsection.description = section_description or section.name
            return subsection
        return None

    def add_film(self):
        # Create a new film.
        self.film = self.festival_data.create_film(self.film_title, self.film_url)
        if self.film is None:
            try:
                self.film = self.festival_data.get_film_by_key(self.film_title, self.film_url)
            except KeyError:
                ERROR_COLLECTOR.add(f'Could not create film:', f'{self.film_title} ({self.film_url})')
            else:
                self.sections_by_film[self.film].append(self.subsection)
        else:
            # Fill details.
            self.film.duration = self.film_duration
            self.film.subsection = self.subsection
            self.film.medium_category = Film.category_by_string['films']
            self.sections_by_film[self.film] = [self.subsection]

            # Add the film to the list.
            self.festival_data.films.append(self.film)

    def set_duration(self):
        try:
            film_length = self.film_property_by_label['length']
        except KeyError:
            minutes = 0
        else:
            minutes = int(film_length.split(' ')[0])  # '84 min'
        self.film_duration = datetime.timedelta(minutes=minutes)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmsParseState.AWAITING_TITLE) and tag == 'meta' and len(attrs) == 2:
            if attrs[0] == ('property', 'og:description') and attrs[1][0] == 'content':
                self.state_stack.change(self.FilmsParseState.IN_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_TITLE) and tag == 'span' and len(attrs):
            if attrs[0][0] == 'title':
                self.section_name = attrs[0][1].strip()
                self.state_stack.change(self.FilmsParseState.AWAITING_DESCR)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_DESCR) and tag == 'div' and len(attrs) == 1:
            if attrs[0] == ('class', 'ey43j5h0 css-uu0j5i-Body-Body'):
                self.state_stack.change(self.FilmsParseState.IN_DESCR)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_URL) and tag == 'article' and len(attrs):
            if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
                self.state_stack.push(self.FilmsParseState.IN_FILM_URL)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_DESCR) and tag == 'article' and len(attrs):
            if attrs[0] == ('class', 'eqiw4yk1 css-scrfvs-Container-Container'):
                self.subsection = self.get_subsection()
                COUNTER.increase('no description')
                self.state_stack.push(self.FilmsParseState.IN_FILM_URL)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_URL) and tag == 'a' and len(attrs):
            if attrs[0][0] == 'href':
                slug = attrs[0][1]
                self.film_url = FESTIVAL_HOSTNAME + slug    # Use literal slug, iri codes are not well understood.
                COUNTER.increase('film URLs')
                self.state_stack.change(self.FilmsParseState.AWAITING_FILM_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_TITLE) and tag == 'h2' and len(attrs) == 3:
            if attrs[0] == ('variant', '4') and attrs[1] == ('clamp', '2'):
                self.state_stack.change(self.FilmsParseState.IN_FILM_TITLE)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTIES):
            if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
                self.metadata_key = attrs[0][1]
                self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTY)
        elif self.state_stack.state_is(self.FilmsParseState.AWAITING_FILM_URL) and tag == 'footer':
            self.state_stack.change(self.FilmsParseState.DONE)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTY) and tag == 'div':
            self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTIES)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTIES) and tag == 'div':
            self.reset_film_parsing()

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmsParseState.IN_DESCR):
            if not data.startswith('.css'):
                section_description = data
                self.subsection = self.get_subsection(section_description)
                self.state_stack.change(self.FilmsParseState.AWAITING_FILM_URL)
            else:
                COUNTER.increase('sections with css data')
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_TITLE):
            self.film_title = data
            COUNTER.increase('film title')
            self.state_stack.change(self.FilmsParseState.IN_FILM_PROPERTIES)
        elif self.state_stack.state_is(self.FilmsParseState.IN_FILM_PROPERTY):
            self.film_property_by_label[self.metadata_key] = data


class FilmPageParser(HtmlPageParser):
    class FilmParseState(Enum):
        IDLE = auto()
        AWAITING_TITLE = auto()
        IN_TITLE = auto()
        AWAITING_META_DICT = auto()
        IN_META_DICT = auto()
        IN_META_PROPERTY = auto()
        AWAITING_PAGE_SECTION = auto()
        IN_PAGE_SECTION = auto()
        AWAITING_ARTICLE = auto()
        IN_ARTICLE = auto()
        AWAITING_SCREENINGS = auto()
        IN_SCREENINGS = auto()
        IN_SCREENING_DATE = auto()
        AWAITING_SCREENING_INFO = auto()
        IN_SCREENING_INFO = auto()
        AWAITING_TIMES = auto()
        IN_TIMES = auto()
        AWAITING_LOCATION = auto()
        IN_LOCATION = auto()
        AWAITING_CREDITS = auto()
        IN_DICT = auto()
        IN_PROPERTY = auto()
        DONE = auto()

    # Instead of developing a new SpecialsPageParser, link special titles
    # and urls by hand.
    url_by_combi_title = {
    }

    re_desc = re.compile(r'(?P<title>.*), (?P<desc>[A-Z].*\.)$')
    re_num_screen = re.compile(r'^(?P<theater>.*?)\s+(?P<number>\d+)$')
    re_colon_screen = re.compile(r'^(?P<theater>.*?):\s+(?P<room>.+)$')
    nl_month_by_name: Dict[str, int] = {'november': 11}

    def __init__(self, festival_data, film, sections, debug_prefix='F', corrected_url=None):
        super().__init__(festival_data, DEBUG_RECORDER, debug_prefix, debugging=DEBUGGING)
        self.film = film
        self.sections = sections
        self.corrected_url = corrected_url
        self.title = film.title
        self.film_property_by_label = {}
        self.film_info = None
        self.duration = None

        # Initialize screening data.
        self.metadata_key = None
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.qa = None
        self.audience = None
        self.extra = None
        self.combi_title = None
        self.init_screening_data()

        # Draw a bar with section info.
        self.print_debug(self.headed_bar(header=str(self.film)))
        if corrected_url:
            COUNTER.increase('corrected urls')

        # Initialize the state stack.
        self.state_stack = self.StateStack(self.print_debug, self.FilmParseState.IDLE)

    def init_screening_data(self):
        self.metadata_key = None
        self.start_date = None
        self.start_dt = None
        self.end_dt = None
        self.screen = None
        self.qa = ''
        self.audience = AUDIENCE_PUBLIC
        self.extra = ''
        self.combi_title = None

    def add_paragraph(self):
        paragraph = self.article_paragraph
        if len(paragraph) > 0:
            self.article_paragraphs.append(paragraph.strip())
        self.article_paragraph = ''

    def set_article(self):
        self.article = '\n\n'.join(self.article_paragraphs)
        self.set_description_from_article(self.film.title)
        COUNTER.increase('articles')

    def add_film_info(self):
        self.film_info = FilmInfo(self.film.film_id, self.description, self.article)
        self.festival_data.filminfos.append(self.film_info)

    def update_film_info(self):
        COUNTER.increase('filminfo update')
        if self.film_property_by_label:
            COUNTER.increase('meta dicts')
            properties = [f'{key}: {value}' for (key, value) in self.film_property_by_label.items()]
            metadata = '\n'.join(properties)
            self.film_info.article += f'\n\n{metadata}'
            COUNTER.increase('filminfo extended')

    def set_screening_date(self, data):
        parts = data.split()  # '10 november'
        try:
            day = int(parts[0])
            month = int(FilmPageParser.nl_month_by_name[parts[1]])
        except ValueError as e:
            COUNTER.increase('improper dates')
            self.print_debug(f'{e} in {self.film}', 'Proceeding to next page section')
            return False
        else:
            self.start_date = datetime.date(day=day, month=month, year=FESTIVAL_YEAR)
        return True

    def set_screening_times(self, data):
        try:
            start_time = datetime.time(int(data[:2]), int(data[3:5]))   # '14.00–15.28'
            end_time = datetime.time(int(data[6:8]), int(data[9:]))
        except ValueError as e:
            COUNTER.increase('improper times')
            self.print_debug(f'{e} in times of {self.film} screening', 'Proceeding to next page section')
            return False
        else:
            start_date = self.start_date
            end_date = start_date if end_time > start_time else start_date + datetime.timedelta(days=1)
            self.start_dt = datetime.datetime.combine(start_date, start_time)
            self.end_dt = datetime.datetime.combine(end_date, end_time)
        return True

    def get_idfa_screen(self, data):
        screen_parse_name = data.strip()
        return get_screen_from_parse_name(self.festival_data, screen_parse_name, self.split_location)

    def split_location(self, location):
        city_name = FESTIVAL_CITY
        theater_parse_name = location
        screen_abbreviation = 'zaal'
        colon_match = self.re_colon_screen.match(location)
        if colon_match:
            theater_parse_name = colon_match.group(1)
            screen_abbreviation = colon_match.group(2)
        else:
            num_match = self.re_num_screen.match(location)
            if num_match:
                theater_parse_name = num_match.group(1)
                screen_abbreviation = num_match.group(2)
        return city_name, theater_parse_name, screen_abbreviation

    def process_screening_info(self, data):
        qa_words = ['gesprek', 'Q&amp;A', 'Talk', 'nagesprek']
        private_words = ['Exclusief', 'Pashouders']
        part_of_prefix = 'Onderdeel van'
        self.qa = 'QA' if len([w for w in qa_words if w in data]) else ''
        self.audience = 'private' if len([w for w in private_words if w in data]) else AUDIENCE_PUBLIC
        if data.startswith(part_of_prefix):
            self.combi_title = data[len(part_of_prefix):].strip()
            self.print_debug('FOUND COMBINATION TITLE', f'{self.combi_title}')

    def add_idfa_screening(self, display=False):
        # Create an IDFA screening from the gathered data.
        self.screening = IdfaScreening(self.film, self.screen, self.start_dt, self.end_dt,
                                       qa=self.qa, audience=self.audience, extra=self.extra,
                                       combi_title=self.combi_title)
        self.add_screening(self.screening, display=display)

        # Prepare combination film data if applicable.
        if self.combi_title in self.url_by_combi_title.keys():
            self.screening.combi_url = self.url_by_combi_title[self.combi_title]
            m = re.match(self.re_desc, self.combi_title)
            if m:
                g = m.groupdict()
                self.combi_title = g['title']
                print(f"{g['title']:-<80}{g['desc']}")
            self.set_combination(self.screening)

        # Reset data as to find the next screening.
        self.init_screening_data()

    def set_combination(self, screening):
        combi_url = screening.combi_url

        # Get the combination film or create it.
        combi_film = self.festival_data.create_film(self.combi_title, combi_url)
        if combi_film is None:
            try:
                combi_film = self.festival_data.get_film_by_key(self.combi_title, combi_url)
            except KeyError:
                ERROR_COLLECTOR.add(f'Could not create combination film:', f'{self.combi_title} ({combi_url})')
                return
        else:
            combi_film.duration = screening.end_datetime - screening.start_datetime
            combi_film.medium_category = Film.category_by_string['combinations']
            self.festival_data.films.append(combi_film)
        combi_screening = IdfaScreening(
            combi_film, screening.screen, screening.start_datetime, screening.end_datetime, audience=AUDIENCE_PUBLIC
        )
        if combi_screening not in combi_film.screenings(self.festival_data):
            self.festival_data.screenings.append(combi_screening)
            COUNTER.increase('combination screenings')

        # Update the combination film info.
        combi_film_info = combi_film.film_info(self.festival_data)
        screened_film_info = self.film.film_info(self.festival_data)
        if not combi_film_info.film_id:
            combi_film_info.film_id = combi_film.film_id
            combi_film_info.description = self.combi_title
            self.festival_data.filminfos.append(combi_film_info)
        if self.film.film_id not in [sf.film_id for sf in combi_film_info.screened_films]:
            screened_film = ScreenedFilm(self.film.film_id, self.film.title, screened_film_info.description)
            combi_film_info.screened_films.append(screened_film)

        # Update the screened film info.
        if combi_film.film_id not in [cf.film_id for cf in screened_film_info.combination_films]:
            screened_film_info.combination_films.append(combi_film)

    def handle_starttag(self, tag, attrs):
        HtmlPageParser.handle_starttag(self, tag, attrs)

        if self.state_stack.state_is(self.FilmParseState.IDLE) and tag == 'script':
            self.state_stack.push(self.FilmParseState.AWAITING_TITLE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_TITLE) and tag == 'h1':
            self.state_stack.change(self.FilmParseState.IN_TITLE)
        elif self.state_stack.state_in([
                self.FilmParseState.AWAITING_META_DICT,
                self.FilmParseState.IN_META_DICT,
                self.FilmParseState.AWAITING_CREDITS]):
            if tag == 'div' and len(attrs) and attrs[0][0] == 'data-meta':
                self.metadata_key = attrs[0][1]
                self.state_stack.change(self.FilmParseState.IN_META_PROPERTY)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_PAGE_SECTION) and tag in ['div', 'h2']:
            if len(attrs) == 2 and attrs[0] == ('variant', '3'):
                if attrs[1] == ('class', 'e10q2t3u0 css-1bg59lt-Heading-Heading-Heading'):
                    self.state_stack.push(self.FilmParseState.IN_PAGE_SECTION)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_ARTICLE) and tag == 'p':
            self.state_stack.change(self.FilmParseState.IN_ARTICLE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_SCREENINGS) and tag == 'div':
            if len(attrs) == 2 and attrs[0] == ('variant', '4'):
                self.state_stack.change(self.FilmParseState.IN_SCREENINGS)
                self.state_stack.push(self.FilmParseState.IN_SCREENING_DATE)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_SCREENING_INFO) and tag == 'div':
            if len(attrs) and attrs[0] == ('class', 'ey43j5h0 css-1cky3te-Body-Body'):
                self.state_stack.change(self.FilmParseState.IN_SCREENING_INFO)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_TIMES) and tag == 'span':
            self.state_stack.change(self.FilmParseState.IN_TIMES)
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENINGS) and tag == 'div' and len(attrs) == 2:
            if attrs[0] == ('variant', '4'):
                self.state_stack.push(self.FilmParseState.IN_SCREENING_DATE)
            elif attrs[0] == ('variant', '3'):
                self.state_stack.change(self.FilmParseState.IN_PAGE_SECTION)

    def handle_endtag(self, tag):
        HtmlPageParser.handle_endtag(self, tag)

        if self.state_stack.state_is(self.FilmParseState.IN_META_PROPERTY) and tag == 'div':
            self.state_stack.change(self.FilmParseState.IN_META_DICT)
        elif self.state_stack.state_is(self.FilmParseState.IN_META_DICT) and tag == 'div':
            print(f'{self.film_property_by_label=}')
            self.print_debug('FOUND DICT', f'{self.film_property_by_label=}')
            self.state_stack.change(self.FilmParseState.AWAITING_PAGE_SECTION)
        elif self.state_stack.state_is(self.FilmParseState.IN_DICT):
            self.state_stack.change(self.FilmParseState.AWAITING_TITLE)
        elif self.state_stack.state_is(self.FilmParseState.IN_ARTICLE):
            if tag == 'p':
                self.add_paragraph()
            elif tag == 'div':
                self.set_article()
                self.add_film_info()
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING_INFO) and tag == 'div':
            self.state_stack.change(self.FilmParseState.AWAITING_TIMES)
        elif self.state_stack.state_is(self.FilmParseState.AWAITING_LOCATION) and tag == 'svg':
            self.state_stack.change(self.FilmParseState.IN_LOCATION)

    def handle_data(self, data):
        HtmlPageParser.handle_data(self, data)

        if self.state_stack.state_is(self.FilmParseState.IN_TITLE):
            self.title = data
            if self.film.title != self.title:
                error_desc = f'"{self.title}" while parsing "{self.film}"'
                debug_text = '\n'.join([
                    error_desc,
                    f'{"registered url":-<20}{self.film.url}',
                    f'{"corrected url":-<20}{self.corrected_url}',
                ])
                ERROR_COLLECTOR.add('DIFFERENT TITLE', error_desc)
                self.print_debug(f'DIFFERENT TITLE: {debug_text}')
            self.state_stack.change(self.FilmParseState.AWAITING_META_DICT)
        elif self.state_stack.state_is(self.FilmParseState.IN_META_PROPERTY):
            self.film_property_by_label[self.metadata_key] = data
        elif self.state_stack.state_is(self.FilmParseState.IN_PAGE_SECTION):
            if data == 'Synopsis':
                self.state_stack.change(self.FilmParseState.AWAITING_ARTICLE)
            elif data.startswith('Tickets'):
                self.state_stack.change(self.FilmParseState.AWAITING_SCREENINGS)
            elif data == 'Credits':
                self.state_stack.change(self.FilmParseState.AWAITING_CREDITS)
            elif data == 'Stills':
                self.update_film_info()
                self.state_stack.change(self.FilmParseState.DONE)
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING_INFO):
            self.process_screening_info(data)
        elif self.state_stack.state_is(self.FilmParseState.IN_ARTICLE):
            if not data.startswith('.css'):
                self.article_paragraph += data
        elif self.state_stack.state_is(self.FilmParseState.IN_SCREENING_DATE):
            if self.set_screening_date(data):
                self.state_stack.change(self.FilmParseState.AWAITING_SCREENING_INFO)
            else:
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_TIMES):
            if self.set_screening_times(data):
                self.state_stack.change(self.FilmParseState.AWAITING_LOCATION)
            else:
                self.state_stack.pop()
        elif self.state_stack.state_is(self.FilmParseState.IN_LOCATION):
            self.screen = self.get_idfa_screen(data)
            self.add_idfa_screening(True)
            self.state_stack.pop()


class IdfaScreening(Screening):
    def __init__(self, film, screen, start_datetime, end_datetime,
                 qa='', extra='', audience=None, combi_title=None, combi_url=None):
        super().__init__(film, screen, start_datetime, end_datetime, qa, extra, audience)
        self.combi_title = combi_title
        self.combi_url = combi_url


class IdfaData(FestivalData):
    duplicates_by_screening = {}

    def __init__(self, directory):
        super().__init__(FESTIVAL_CITY, directory)
        self.compilation_by_url = {}

    def film_key(self, title, url):
        return url

    def screening_can_go_to_planner(self, screening):
        can_go = screening.is_public()
        if can_go:
            try:
                self.duplicates_by_screening[screening] += 1
                can_go = False
            except KeyError:
                self.duplicates_by_screening[screening] = 0
        if can_go:
            can_go = screening.combi_url is None
        # if can_go:
        #     can_go = screening.screen.screen_id != 126      # de Brakke Grond
        if can_go:
            can_go = not self.is_coinciding(screening)
        return can_go

    def film_can_go_to_planner(self, film_id):
        return True

    def is_coinciding(self, screening):
        # Get the film info.
        film_info = screening.film.film_info(self)

        # Check if the film is a combination program.
        screened_films = film_info.screened_films
        if len(screened_films):
            return False

        # Check if the film is screened as part of a combination
        # program.
        combination_films = film_info.combination_films
        if len(combination_films):
            key = ScreeningKey(screening)
            for combination_film in combination_films:
                for combination_screening in combination_film.screenings(self):
                    if key == ScreeningKey(combination_screening):
                        return True

        # This screening doesn't coincide with a combination program.
        return False


if __name__ == "__main__":
    main()

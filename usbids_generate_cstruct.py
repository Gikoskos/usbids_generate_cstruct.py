#!/usr/bin/env python3 

from urllib.request import Request, urlopen
from time import strftime
from sys import argv
import re


#Change these however you like
usbid_struct = {
    'name': 'UsbDevStruct',
    'vendorid': 'VendorID',
    'deviceid': 'DeviceID',
    'vendorname': 'Vendor',
    'devicename': 'Device',
    'nametype': 'char*',
    'idtype': 'unsigned short',
    'arrayname': 'UsbList'
}
date_str = strftime('%c %z')
src_fname = 'usbids.c'
hdr_fname = 'usbids.h'


index_url = 'http://www.linux-usb.org/usb.ids'

ignored_line_pattern = re.compile('(^#.*\n)|(^[ \t\r]*\n)') #comments or empty lines
endoflist_str = "# List of known device classes, subclasses and protocols\n"

ignored = 0 #these are just flags, they have no special meaning
endoflist = 1

patterns = [
    re.compile('^(?P<id>[0-9a-fA-F]{4})  (?P<name>.+)'), #vendor
    re.compile('^\t(?P<id>[0-9a-fA-F]{4})  (?P<name>.+)'), #device
    re.compile('^\t\t(?P<id>[0-9a-fA-F]{4})  (?P<name>.+)') #interface
]


file_prologue = r"""/*
 * This file was auto-generated by {module_name}. Don't edit!
 * {gen_date}
 */

#include <stdlib.h> //for NULL, bsearch
#include "usbids.h"

{usbid[name]} {usbid[arrayname]}[] = {{
"""

file_epilogue = r"""}};
/*
 * Total vendors: {}
 * Total devices: {}
 */

unsigned int {usbid[arrayname]}Length = sizeof {usbid[arrayname]} / sizeof {usbid[arrayname]}[0];

static int cmp(const void *vp, const void *vq)
{{
	const {usbid[name]} *p = vp;
	const {usbid[name]} *q = vq;

	if (p->{usbid[vendorid]} > q->{usbid[vendorid]}) {{
        return 1;
    }} else if (p->{usbid[vendorid]} < q->{usbid[vendorid]}) {{
        return -1;
    }} else if (p->{usbid[deviceid]} > q->{usbid[deviceid]}) {{
        return 1;
    }} else if (p->{usbid[deviceid]} < q->{usbid[deviceid]}) {{
        return -1;
    }}

	return 0;
}}

{usbid[name]} *{usbid[arrayname]}Find({usbid[idtype]} vendor, {usbid[idtype]} device)
{{
	{usbid[name]} key;

	key.{usbid[vendorid]} = vendor;
	key.{usbid[deviceid]} = device;
	return bsearch(&key, {usbid[arrayname]}, {usbid[arrayname]}Length, sizeof *{usbid[arrayname]}, cmp);
}}

int {usbid[arrayname]}IsSorted(void)
{{
	unsigned int i;

	for (i = 1; i < {usbid[arrayname]}Length; i++) {{
		if (cmp(&{usbid[arrayname]}[i - 1], &{usbid[arrayname]}[i]) > 0) {{
			return 0;
        }}
    }}

	return 1;
}}

//these are just needed for the tests
#include <assert.h>
#include <string.h>

void {usbid[arrayname]}RunTests(void)
{{
    unsigned int i;
    {usbid[name]}* tmpDev;

    assert({usbid[arrayname]}IsSorted());

    for (i = 0; i < {usbid[arrayname]}Length; i++) {{
        tmpDev = {usbid[arrayname]}Find({usbid[arrayname]}[i].{usbid[vendorid]}, {usbid[arrayname]}[i].{usbid[deviceid]});

        assert(tmpDev);
        assert(tmpDev->Vendor);
        assert(tmpDev->{usbid[vendorid]} == {usbid[arrayname]}[i].{usbid[vendorid]});
        assert(tmpDev->{usbid[deviceid]} == {usbid[arrayname]}[i].{usbid[deviceid]});

        assert(strcmp(tmpDev->{usbid[vendorname]}, {usbid[arrayname]}[i].{usbid[vendorname]}));

        if (!tmpDev->{usbid[devicename]}) {{
            assert(tmpDev->{usbid[devicename]} == {usbid[arrayname]}[i].{usbid[devicename]});
        }} else {{
            assert(strcmp(tmpDev->{usbid[devicename]}, {usbid[arrayname]}[i].{usbid[devicename]}));
        }}
    }}
}}
"""

header_file = r"""/*
 * This file was auto-generated by {module_name}. Don't edit!
 * {gen_date}
 */

#ifndef USB_IDS_H
#define USB_IDS_H

typedef struct {{
	{usbid[idtype]} {usbid[vendorid]};
	{usbid[idtype]} {usbid[deviceid]};
	{usbid[nametype]} {usbid[vendorname]};
	{usbid[nametype]} {usbid[devicename]};
}} {usbid[name]};

extern {usbid[name]} {usbid[arrayname]}[];
extern unsigned int {usbid[arrayname]}Length;

{usbid[name]} *{usbid[arrayname]}Find({usbid[idtype]} vendor, {usbid[idtype]} device);
int {usbid[arrayname]}IsSorted(void);
void {usbid[arrayname]}RunTests(void);

#endif
"""


def skip_comments(page):
    for line in page:
        line = line.decode('utf-8')
        match = ignored_line_pattern.search(line)
        if match is None:
            return line
    return None

def parse(line):
    for i, pattern in enumerate(patterns):
        #order of searches is important here!
        match = pattern.search(line)

        if match is not None:
            return i, match.group('id'), match.group('name')

        if line == endoflist_str:
            return endoflist

        if ignored_line_pattern.search(line) is not None:
            return ignored

    return None


with urlopen(Request(index_url)) as page:
    first_line = skip_comments(page)
    data = parse(first_line)
    vendor_cnt = 0
    device_cnt = 0
    no_devices_for_previous_vendor = True

    with open(src_fname, 'w') as usbids_src:

        def write_vendor(vendor):
            usbids_src.write('\t{{ 0x{}, 0x0000, "{}", NULL }},\n'.format(
                vendor[1], vendor[2].replace('\\', '\\\\').replace(r'"', r'\"'),
            ))

        def write_device(vendor, device):
            usbids_src.write('\t{{ 0x{}, 0x{}, "{}", "{}" }},\n'.format(
                vendor[1], device[1],
                vendor[2].replace('\\', '\\\\').replace(r'"', r'\"'),
                device[2].replace('\\', '\\\\').replace(r'"', r'\"'),
            ))


        usbids_src.write(file_prologue.format(module_name=argv[0], gen_date=date_str, usbid=usbid_struct))

        if data is not ignored and data[0] == 0:
            curr_vendor = data
            vendor_cnt += 1

        for line in page:
            line = line.decode('utf-8')

            data = parse(line)
            if data is None:
                raise RuntimeError('Failed parsing line "{}"'.format(line.strip('\n')))

            if data == ignored:
                continue

            if data == endoflist:
                break

            if data[0] == 0:
                if no_devices_for_previous_vendor:
                    write_vendor(curr_vendor)

                curr_vendor = data
                vendor_cnt += 1
                no_devices_for_previous_vendor = True

            elif data[0] == 1:
                no_devices_for_previous_vendor = False
                write_device(curr_vendor, data)
                device_cnt += 1
            #ignore interfaces
            #elif data[0] == 2:

        usbids_src.write(file_epilogue.format(vendor_cnt, device_cnt, usbid=usbid_struct))

with open(hdr_fname, 'w') as usbids_hdr:
    usbids_hdr.write(header_file.format(module_name=argv[0], gen_date=date_str, usbid=usbid_struct))
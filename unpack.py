#!/usr/bin/env python

import os
from os.path import join as pjoin, basename, dirname, splitext, exists
import argparse
import numpy
import h5py
from rasterio.enums import Resampling

import yaml
from yaml.representer import Representer

from gaip.acquisition import acquisitions
from gaip.data import write_img
from gaip.hdf5 import find
from gaip.geobox import GriddedGeoBox

yaml.add_representer(numpy.int8, Representer.represent_int)
yaml.add_representer(numpy.uint8, Representer.represent_int)
yaml.add_representer(numpy.int16, Representer.represent_int)
yaml.add_representer(numpy.uint16, Representer.represent_int)
yaml.add_representer(numpy.int32, Representer.represent_int)
yaml.add_representer(numpy.uint32, Representer.represent_int)
yaml.add_representer(numpy.int, Representer.represent_int)
yaml.add_representer(numpy.int64, Representer.represent_int)
yaml.add_representer(numpy.uint64, Representer.represent_int)
yaml.add_representer(numpy.float, Representer.represent_float)
yaml.add_representer(numpy.float32, Representer.represent_float)
yaml.add_representer(numpy.float64, Representer.represent_float)
yaml.add_representer(numpy.ndarray, Representer.represent_list)

PRODUCTS = ['NBAR', 'NBART']
LEVELS = [2, 4, 8, 16, 32]


def unpack(scene, granule, h5group, outdir):
    """
    Unpack and package the NBAR and NBART products.
    """
    # listing of all datasets of IMAGE CLASS type
    img_paths = find(h5group, 'IMAGE')

    for product in PRODUCTS:
        for pathname in [p for p in img_paths if '/{}/'.format(product) in p]:

            dataset = h5group[pathname]
            acqs = scene.get_acquisitions(group=pathname.split('/')[0],
                                          granule=granule)
            acq = [a for a in acqs if
                   a.band_name == dataset.attrs['band_name']][0]

            # base_dir = pjoin(splitext(basename(acq.pathname))[0], granule)
            base_fname = '{}.TIF'.format(splitext(basename(acq.uri))[0])
            out_fname = pjoin(outdir,
                              # base_dir.replace('L1C', 'ARD'),
                              granule.replace('L1C', 'ARD'),
                              product,
                              base_fname.replace('L1C', product))

            # output
            if not exists(dirname(out_fname)):
                os.makedirs(dirname(out_fname))

            write_img(dataset, out_fname, cogtif=True, levels=LEVELS,
                      nodata=dataset.attrs['no_data_value'],
                      geobox=GriddedGeoBox.from_dataset(dataset),
                      resampling=Resampling.nearest,
                      options={'blockxsize': dataset.chunks[1],
                               'blockysize': dataset.chunks[0],
                               'compress': 'deflate',
                               'zlevel': 4})

    # retireve metadata
    scalar_paths = find(h5group, 'SCALAR')
    pathname = [pth for pth in scalar_paths if 'NBAR-METADATA' in pth][0]
    tags = yaml.load(h5group[pathname][()])

    # output metadata
    out_fname = pjoin(outdir,
                      # base_dir.replace('L1C', 'ARD'),
                      granule.replace('L1C', 'ARD'),
                      'ARD-METADATA.yaml')
    with open(out_fname, 'w') as src:
        yaml.dump(tags, src, default_flow_style=False, indent=4)


def main(l1_path, gaip_fname, outdir):
    """
    Main level
    """
    scene = acquisitions(l1_path)
    with h5py.File(gaip_fname, 'r') as fid:
        for granule in scene.granules:
            if granule is None:
                h5group = fid['/']
            else:
                h5group = fid[granule]

            unpack(scene, granule, h5group, outdir)


if __name__ == '__main__':
    description = "Prepare or package a gaip output."
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--level1-pathname", required=True,
                        help="The level1 pathname.")
    parser.add_argument("--filename", required=True,
                        help="The filename of the gaip output.")
    parser.add_argument("--outdir", required=True,
                        help="The output directory.")

    args = parser.parse_args()

    main(args.level1_pathname, args.filename, args.outdir)
import math
import cv2
import json
import tensorflow as tf
import numpy as np
import skimage.io as io
import skimage.feature as ft
import skimage.transform as trf
import tempfile
import os, sys
import matplotlib.pyplot as plt

from PIL import Image
from skimage.filters.rank import otsu
from skimage.filters import threshold_otsu, rank
from skimage import color
from skimage.morphology import disk
from skimage import feature
from skimage.util import img_as_ubyte
from bokeh.io.export import get_screenshot_as_png


from bokeh.io import output_file, show, output_notebook
from bokeh.models import (
    GMapPlot,
    GMapOptions,
    ColumnDataSource,
    MultiLine,
    Circle,
    ImageRGBA,
    ImageURL,
    Range1d,
    PanTool,
    WheelZoomTool,
    BoxSelectTool,
)

from bokeh.plotting import figure


def estimate_sign_coords(coords, azimuth, reference_text_height):
    pano_lat = coords["lat"]
    pano_lng = coords["lng"]
    m_per_deg_lat = (
        111132.954
        - 559.822 * math.cos(2.0 * pano_lat * math.pi / 180.0)
        + 1.175 * math.cos(4.0 * pano_lat * math.pi / 180.0)
    )
    m_per_deg_lng = (math.pi / 180) * 6367449 * math.cos(pano_lat * math.pi / 180.0)
    distance = 0.05 / math.tan(reference_text_height / 512.0 * 10.0 * math.pi / 180.0)
    distance_lat = math.cos(azimuth * math.pi / 180.0) * distance / m_per_deg_lat
    distance_lng = math.sin(azimuth * math.pi / 180.0) * distance / m_per_deg_lng

    new_lat = pano_lat + distance_lat
    new_lng = pano_lng + distance_lng
    return (new_lat, new_lng)


def calculate_min_distance(lat_list_sign_ex, lng_list_sign_ex, lat_sign, lng_sign):
    min_distance = sys.maxsize
    for old_sign_lat, old_sign_lng in zip(lat_list_sign_ex, lng_list_sign_ex):
        R = 6367449.0
        old_lat = old_sign_lat * math.pi / 180.0
        old_lng = old_sign_lng * math.pi / 180.0
        new_lat = lat_sign * math.pi / 180.0
        new_lng = lng_sign * math.pi / 180.0

        dlat = old_lat - new_lat
        dlng = old_lng - new_lng
        a = (math.sin(dlat / 2)) ** 2 + math.cos(new_lat) * math.cos(old_lat) * (
            math.sin(dlng / 2)
        ) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        next_distance = R * c
        if next_distance < distance:
            min_distance = next_distance
    return min_distance


tfsegm_root_dir = "./tf-segm"
test_dumps_path = os.path.join(tfsegm_root_dir, "images_right/downloaded")
test_painted_path = "./SignsTest/static"

test_data_path = os.path.join(tfsegm_root_dir, "images_right/slicedtosigns_evaltrf/")

jsons_coords = {}
with open(os.path.join(test_dumps_path, "mapscan1.json")) as json_file:
    jsons_coords = json.load(json_file)

cutIndex = 0

lat_list_sign = []
lng_list_sign = []
lat_list_pano = []
lng_list_pano = []
img_list = []
links_list_lat = []
links_list_lng = []

if not os.path.exists(test_painted_path):
    os.makedirs(test_painted_path)

for parent, dirnames, filenames in os.walk(test_data_path):
    for filename in filenames:
        if filename.startswith("sign."):
            with open(os.path.join(parent, filename)) as f1:
                config1 = json.load(f1)
                # print(config1)
                if len(config1["boxes"]) == 0:
                    print("skipping empty sign")
                    continue
                cutIndex += 1

                with open(config1["config_file"]) as f2:
                    config2 = json.load(f2)
                    # print(config2['pano_id'])

                    coords = jsons_coords[config2["pano_id"]]

                    for box in config1["boxes"]:
                        tform = trf.ProjectiveTransform()
                        if tform.estimate(
                            np.array(config2["dst"]), np.array(config2["src"])
                        ):
                            warped_coords = tform.inverse(np.array(box["dst"]))
                            box["dst_warped"] = warped_coords

                    tile_fn = (
                        "_"
                        + str(config2["heading"])
                        + "_"
                        + str(config2["delta"])
                        + ".jpg"
                    )
                    tile_fpath = os.path.join(
                        test_dumps_path, config2["pano_id"], tile_fn
                    )
                    meta_fn = "metadata.json"
                    meta_fpath = os.path.join(
                        test_dumps_path, config2["pano_id"], meta_fn
                    )
                    with open(meta_fpath) as fmeta:
                        meta_config = json.load(fmeta)
                        try:
                            yaw = float(meta_config["Projection"]["pano_yaw_deg"])
                        except:
                            # print('metadata query failed - skipping sign :(')
                            continue

                    im_clean = cv2.imread(tile_fpath)[:, :, ::-1].copy()
                    im = im_clean.copy()

                    box_fullsign = np.array(config2["dst"]).astype(np.int32)
                    cv2.polylines(
                        im,
                        [box_fullsign.reshape((-1, 1, 2))],
                        True,
                        color=(0, 255, 0),
                        thickness=1,
                    )
                    towzone_text_height = 8
                    if len(config1["boxes"]) < 8:
                        continue
                    for box in config1["boxes"]:
                        box_signtext = np.array(box["dst_warped"]).astype(np.int32)
                        if box["result"] == "TOW" or box["result"] == "ZONE":
                            towzone_text_height = max(
                                box["dst_warped"][3][1] - box["dst_warped"][1][1],
                                max(
                                    box["dst_warped"][2][1] - box["dst_warped"][0][1],
                                    towzone_text_height,
                                ),
                            )
                            # print(towzone_text_height)
                            cv2.polylines(
                                im,
                                [box_signtext.reshape((-1, 1, 2))],
                                True,
                                color=(255, 255, 0),
                                thickness=1,
                            )
                        else:
                            cv2.polylines(
                                im,
                                [box_signtext.reshape((-1, 1, 2))],
                                True,
                                color=(150, 150, 0),
                                thickness=1,
                            )

                        cv2.putText(
                            im,
                            box["result"],
                            (
                                int((box_signtext[2][0] - box_fullsign[0][0]) * 3 + 10),
                                int((box_signtext[2][1] - box_fullsign[0][1]) * 3 + 10),
                            ),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6,
                            (255, 255, 0),
                            2,
                            cv2.LINE_AA,
                        )

                    (fname, fext) = os.path.splitext(filename)
                    painted_sign_fpath = os.path.join(test_painted_path, fname + ".jpg")
                    url_name = os.path.join("static/", fname + ".jpg")
                    if not os.path.exists(painted_sign_fpath):
                        cv2.imwrite(painted_sign_fpath, im[:, :, ::-1])

                    heading_angle = (
                        yaw + config2["heading"] + config2["delta"] / 2 - 180.0
                    )
                    if heading_angle >= 360:
                        heading_angle -= 360
                    if heading_angle < 0:
                        heading_angle += 360

                    (sign_lat, sign_lng) = estimate_sign_coords(
                        coords, heading_angle, towzone_text_height
                    )

                    add_item = True
                    distance = calculate_min_distance(
                        lat_list_sign, lng_list_sign, sign_lat, sign_lng
                    )
                    if distance < 16:
                        add_item = False

                    if not add_item:
                        continue

                    fig = plt.figure(figsize=(15, 7))
                    fig.add_subplot(1, 3, 1)
                    plt.imshow(im_clean)

                    fig.add_subplot(1, 3, 2)
                    plt.imshow(im)

                    item_source = ColumnDataSource(
                        data=dict(
                            latp=[coords["lat"]],
                            lngp=[coords["lng"]],
                            lats=[sign_lat],
                            lngs=[sign_lng],
                            linkslat=[[coords["lat"], sign_lat]],
                            linkslng=[[coords["lng"], sign_lng]],
                        )
                    )

                    item_map_options = GMapOptions(
                        lat=coords["lat"],
                        lng=coords["lng"],
                        map_type="roadmap",
                        zoom=19,
                    )
                    item_plot = GMapPlot(
                        x_range=Range1d(),
                        y_range=Range1d(),
                        map_options=item_map_options,
                    )
                    item_plot.api_key = "####################################"

                    item_circle_sign = Circle(
                        x="lngs",
                        y="lats",
                        size=15,
                        fill_color="red",
                        fill_alpha=0.8,
                        line_color=None,
                    )
                    item_circle_pano = Circle(
                        x="lngp",
                        y="latp",
                        size=15,
                        fill_color="blue",
                        fill_alpha=0.8,
                        line_color=None,
                    )
                    item_links = MultiLine(
                        xs="linkslng", ys="linkslat", line_color="#FFFF00", line_width=2
                    )
                    item_plot.add_glyph(item_source, item_circle_sign)
                    item_plot.add_glyph(item_source, item_circle_pano)
                    item_plot.add_glyph(item_source, item_links)
                    item_plot.plot_width = 400
                    item_plot.plot_height = 400

                    item_img_map = get_screenshot_as_png(item_plot)

                    fig.add_subplot(1, 3, 3)
                    plt.imshow(np.asarray(item_img_map))
                    plt.show()

                    for box in config1["boxes"]:
                        print(f'Detected text:{box["result"]}')

                    lat_list_pano.append(coords["lat"])
                    lng_list_pano.append(coords["lng"])
                    lat_list_sign.append(sign_lat)
                    lng_list_sign.append(sign_lng)
                    links_list_lat.append([coords["lat"], sign_lat])
                    links_list_lng.append([coords["lng"], sign_lng])
                    img_list.append(url_name)
                    # break;

map_options = GMapOptions(lat=41.8959131, lng=-87.6268153, map_type="roadmap", zoom=15)

output_notebook()
plot = GMapPlot(x_range=Range1d(), y_range=Range1d(), map_options=map_options)
plot.title.text = "Test1"

# this one needs to be set
plot.api_key = "##############################"


source = ColumnDataSource(
    data=dict(
        lat=lat_list_pano,
        lng=lng_list_pano,
        lats=lat_list_sign,
        lngs=lng_list_sign,
        linkslat=links_list_lat,
        linkslng=links_list_lng,
    )
)

circle_sign = Circle(
    x="lngs", y="lats", size=5, fill_color="red", fill_alpha=0.8, line_color=None
)
circle_pano = Circle(
    x="lng", y="lat", size=5, fill_color="blue", fill_alpha=0.8, line_color=None
)
links = MultiLine(xs="linkslng", ys="linkslat", line_color="#FFFF00", line_width=2)
plot.add_glyph(source, circle_sign)
plot.add_glyph(source, circle_pano)
plot.add_glyph(source, links)
plot.plot_width = 400
plot.plot_height = 500
plot.add_tools(PanTool(), WheelZoomTool(), BoxSelectTool())

img_map = get_screenshot_as_png(plot)

io.imshow(np.asarray(img_map))
io.show()

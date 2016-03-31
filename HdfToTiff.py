# -*- coding: utf-8 -*-

from osgeo import gdal, ogr, osr
import struct, numpy
import os
import re
import codecs
import datetime
from os import listdir
from os.path import isfile, join

class looker(object):
    """let you look up pixel value"""

    def __init__(self, tifname='test.tif'):
        """Give name of tif file (or other raster data?)"""

        # open the raster and its spatial reference
        self.ds = gdal.Open(tifname)
        srRaster = osr.SpatialReference(self.ds.GetProjection())

        # get the WGS84 spatial reference
        srPoint = osr.SpatialReference()
        srPoint.ImportFromEPSG(4326)  # WGS84

        # coordinate transformation
        self.ct = osr.CoordinateTransformation(srPoint, srRaster)

        # geotranformation and its inverse
        gt = self.ds.GetGeoTransform()
        dev = (gt[1] * gt[5] - gt[2] * gt[4])
        gtinv = (gt[0], gt[5] / dev, -gt[2] / dev,
                 gt[3], -gt[4] / dev, gt[1] / dev)
        self.gt = gt
        self.gtinv = gtinv

        # band as array
        b = self.ds.GetRasterBand(1)
        self.arr = b.ReadAsArray()

    def lookup(self, lon, lat):
        """look up value at lon, lat"""

        # get coordinate of the raster
        xgeo, ygeo, zgeo = self.ct.TransformPoint(lon, lat, 0)

        # convert it to pixel/line on band
        u = xgeo - self.gtinv[0]
        v = ygeo - self.gtinv[3]
        # FIXME this int() is probably bad idea, there should be
        # half cell size thing needed
        xpix = int(self.gtinv[1] * u + self.gtinv[2] * v)
        ylin = int(self.gtinv[4] * u + self.gtinv[5] * v)

        # look the value up
        return self.arr[ylin, xpix]




# 參數設定區
hdfFolderLocation = "C:\Users\hunter\Desktop\hdf"
hdfFileLocation = "C:\Users\hunter\Desktop\GIS\MOD04_L2.A2011028.0155.051.2011033055902.hdf"
subDataSet = "Optical_Depth_Land_And_Ocean"
hdrFileName = "temp_hdr"

srcTif = "C:\Users\hunter\Desktop\GIS\MOD04_L2.A2011028.0155.051.2011033055902_mod04.tif"
convertedTif = './test2.tif'
siteShp = 'C:/Users/hunter/Desktop/GIS/site/site.shp'

logFileName = "log.txt"
csvFileName = "result.csv"

# log
logFile = open(logFileName, "w")
logStr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S  ') + "Start processing all hdf files"
logFile.write(logStr)

# 抓出資料夾內的所有hdf 檔案名稱
hdfFiles = [f for f in listdir(hdfFolderLocation) if isfile(join(hdfFolderLocation, f))]
for f in hdfFiles:
    print(f)

# 生成hdr檔案
commandStr = "hegtool -m " + hdfFileLocation + " " + hdrFileName
os.system(commandStr)

# 讀取出 SWATH_X_PIXEL_RES_METERS, SWATH_Y_PIXEL_RES_METERS, SPATIAL_SUBSET_UL_CORNER, SPATIAL_SUBSET_LR_CORNER
hdrFileName = open(hdrFileName, 'r')
for line in hdrFileName:
    if "SWATH_X_PIXEL_RES_METERS" in line:
        matcher = re.search('[\d.]+', line)
        tempStr = matcher.group(0)
        SWATH_X_PIXEL_RES_METERS = round(float(tempStr))
    if "SWATH_Y_PIXEL_RES_METERS" in line:
        matcher = re.search('[\d.]+', line)
        tempStr = matcher.group(0)
        SWATH_Y_PIXEL_RES_METERS = round(float(tempStr))
    if "SWATH_LAT_MIN" in line:
        matcher = re.search('[\d.]+', line)
        SWATH_LAT_MIN = matcher.group(0)
    if "SWATH_LAT_MAX" in line:
        matcher = re.search('[\d.]+', line)
        SWATH_LAT_MAX = matcher.group(0)
    if "SWATH_LON_MIN" in line:
        matcher = re.search('[\d.]+', line)
        SWATH_LON_MIN = matcher.group(0)
    if "SWATH_LON_MAX" in line:
        matcher = re.search('[\d.]+', line)
        SWATH_LON_MAX = matcher.group(0)

# 準備swath參數檔
parameterFileLocation = "temp_swath"

outputPixelSizeXStr = "OUTPUT_PIXEL_SIZE_X = " + str(SWATH_X_PIXEL_RES_METERS) + "\n"
outputPixelSizeYStr = "OUTPUT_PIXEL_SIZE_Y = " + str(SWATH_Y_PIXEL_RES_METERS) + "\n"
spatialSubsetUlCornerStr = "SPATIAL_SUBSET_UL_CORNER = ( " + SWATH_LAT_MAX + " " + SWATH_LON_MIN + " )" + "\n"
spatialSubsetLrCornerStr = "SPATIAL_SUBSET_LR_CORNER = ( " + SWATH_LAT_MIN + " " + SWATH_LON_MAX + " )" + "\n"

sectionStr1 = "\nNUM_RUNS = 1\n\nBEGIN\nINPUT_FILENAME = " + hdfFileLocation + "\n"
sectionStr2 = "OBJECT_NAME = mod04\nFIELD_NAME = " + subDataSet + "|\nBAND_NUMBER = 1\n" + outputPixelSizeXStr + outputPixelSizeYStr + spatialSubsetUlCornerStr + spatialSubsetLrCornerStr
sectionStr3 = "RESAMPLING_TYPE = NN\nOUTPUT_PROJECTION_TYPE = SIN\nELLIPSOID_CODE = WGS84\n" + \
              "OUTPUT_PROJECTION_PARAMETERS = ( 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0  )\nOUTPUT_FILENAME = " + srcTif + "\n"
sectionStr4 = "OUTPUT_TYPE = GEO\nEND\n\n"

parameterStr = sectionStr1 + sectionStr2 + sectionStr3 + sectionStr4

parameterFile = codecs.open(parameterFileLocation, "w", "utf-8")
parameterFile.write(parameterStr)
parameterFile.close()

# 執行 swtif 使用HEG將hdf轉換成tif
os.system("swtif -p " + parameterFileLocation)
# os.system("swtif -p 123batch_swath")



# 轉換tif成為EPSG:3826投影格式
os.system(
    "\"C:/Program Files (x86)/GDAL/gdalwarp.exe\" -overwrite -s_srs EPSG:53008 -t_srs EPSG:3826 -dstnodata -9999 -of GTiff " + srcTif + " " + convertedTif + "")

# 取得各測站資料
rasterFile = gdal.Open(convertedTif)
geoTransform = rasterFile.GetGeoTransform()
rasterBand = rasterFile.GetRasterBand(1)

vectorFile = ogr.Open(siteShp)

layer = vectorFile.GetLayer()
print(layer.GetFeatureCount())

siteEngNameList = []
aodList = []
for feature in layer:
    siteEngName = feature.GetFieldAsString(1)
    print(siteEngName)
    siteEngNameList.append(siteEngName)

    lon = feature.GetFieldAsDouble(6)
    lat = feature.GetFieldAsDouble(7)
    print(lon)
    print(lat)

    l = looker(convertedTif)
    aod = l.lookup(lon, lat)
    print aod
    aodList.append(aod)

siteEngNameListStr = ','.join(siteEngNameList)
aodListStr = ','.join(str(aod) for aod in aodList)

print(siteEngNameListStr)
print(aodListStr)
csvFile = open(csvFileName, "w")
csvFile.write(siteEngNameListStr)

# 將測站資料寫入csv
oldFilename = 'MOD04_L2.A2011028.0155.051.2011033055902.hdf'
year = int(oldFilename[10:14])
dayOfYear = int(oldFilename[14:17])
hour = int(oldFilename[18:20])
minute = int(oldFilename[20:22])
date = datetime.datetime(year, 1, 1, hour, minute) + datetime.timedelta(
    dayOfYear - 1)  # This assumes that the year is 2007
newFilename = date.strftime('%Y-%m-%d %H:%M')
print(newFilename)

# 關閉csv及log檔案
logFile.close()

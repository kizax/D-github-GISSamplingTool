# -*- coding: utf-8 -*-

import codecs
import datetime
import os
import re
from os import listdir
from os.path import isfile, join
from osgeo import gdal, ogr
from pack import looker


def generateHdr(hdfFileLocation, hdrFileName):
    commandStr = "hegtool -m " + hdfFileLocation + " " + hdrFileName
    os.system(commandStr)
    return None


def generateParameterFile(hdrFileName, parameterFileLocation):
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
    return None


def getAllSiteAodResult(convertedTif, siteShp):
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

        l = looker.Looker(convertedTif)
        aod = l.lookup(lon, lat)
        print aod
        aodList.append(aod)

    siteEngNameListStr = ','.join(siteEngNameList)
    aodListStr = ','.join(str(aod) for aod in aodList)

    print(siteEngNameListStr)
    print(aodListStr)

    return aodListStr


# 參數設定區
hdfFolderLocation = "C:\Users\hunter\Desktop\hdf"
hdfFileLocation = "C:\Users\hunter\Desktop\GIS\MOD04_L2.A2011028.0155.051.2011033055902.hdf"
subDataSet = "Optical_Depth_Land_And_Ocean"
hdrFileName = "temp_hdr"
parameterFileLocation = "temp_swath"

srcTif = "C:\Users\hunter\Desktop\GIS\MOD04_L2.A2011028.0155.051.2011033055902_mod04.tif"
convertedTif = './test2.tif'
siteShp = 'C:/Users/hunter/Desktop/GIS/site/site.shp'

logFileName = "log.txt"
csvFileName = "result.csv"

# 準備log
logFile = open(logFileName, "a")
logStr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S  ') + "Start processing all hdf files\n"
logFile.write(logStr)

# 抓出資料夾內的所有hdf 檔案名稱
hdfFiles = [f for f in listdir(hdfFolderLocation) if isfile(join(hdfFolderLocation, f))]
for f in hdfFiles:
    print(f)

# 生成hdr檔案
generateHdr(hdfFileLocation, hdrFileName)

# 生成參數檔
generateParameterFile(hdrFileName, parameterFileLocation)

# 執行 swtif 使用HEG將hdf轉換成tif
os.system("swtif -p " + parameterFileLocation)

# 轉換tif成為EPSG:3826投影格式
os.system(
    "\"C:/Program Files (x86)/GDAL/gdalwarp.exe\" -overwrite -s_srs EPSG:53008 -t_srs EPSG:3826 -dstnodata -9999 -of GTiff " + srcTif + " " + convertedTif + "")

# 取得各測站資料
aodListStr = getAllSiteAodResult(convertedTif, siteShp)

csvFile = open(csvFileName, "a")
csvFile.write(aodListStr)

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
csvFile.close()
logFile.close()

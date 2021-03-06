# encoding: utf-8
import numpy as np
import cv2
import os
from os import listdir
from os.path import join
from detecter import BB, Detect
import sys
import random
import cPickle
import six
import xml.etree.ElementTree as ET
import logging
from progressbar import ProgressBar
from numpy.random import rand, sample
from skimage.io import show, imshow



def debug_show(crop):
    cv2.imshow('sample', crop)
    q = cv2.waitKey(100)
    if q == ord('q'):
        sys.exit(0)


def randomSample(image, mask, patchSize):
    height, width, c = image.shape
    x = int(rand() * (width - patchSize))
    y = int(rand() * (height - patchSize))
    crop = image[y:y+patchSize, x:x+patchSize, :]    
    area = np.zeros([height, width])
    area[y:y+patchSize, x:x+patchSize] = area[y:y+patchSize, x:x+patchSize] + 1
    area = area + mask
    iou = np.float(len(np.where(area == 2)[0])) / (patchSize * patchSize)
    if iou > 0.7:
        return None
    else:
        return crop
    
    
    
""" 枚数の上限 """
def fx(item_min, item_max) :
    if item_min < item_max:
        return item_min
    else:
        return item_max


if __name__ == '__main__':
    DEBUG = False
    root_dir = '../data'
    annotation_dir = os.path.join(root_dir, 'Annotations')
    image_dir = os.path.join(root_dir, 'Images')
    output_size = (48, 48)
    logging.basicConfig(filename='runtime.log', filemode='w', level=logging.DEBUG)
    progress = ProgressBar()
    progress.min_value = 0
    progress.max_value = len(listdir(image_dir))

    time = 0
    for imagefile in listdir(image_dir):
        positive = []
        negative = []
        time = time+1
        progress.update(time)
        annotation_file = os.path.join(annotation_dir,  imagefile.split('.')[0] + '.xml')
        try: 
            assert os.path.isfile(annotation_file) , '{} was not found.'.format(annotation_file)
        except:
            logging.error('{} was not found.'.format(annotation_file))
            continue
        """ 画像読み込み """
        image = cv2.imread(os.path.join(image_dir, imagefile))
        """xmlからポジティブ領域を切り出しSelective-search の結果でポジティブサンプリング"""
        image_copy = image.copy()
        mask = np.zeros([image.shape[0], image.shape[1]])
        root = ET.parse(annotation_file).getroot()

        """ 値札のBBを取得 """
        for obj in root.findall('.//object'):
            bndbox = obj.find('.//bndbox')
            xmin = int(bndbox.find('.//xmin').text)
            ymin = int(bndbox.find('.//ymin').text)
            xmax = int(bndbox.find('.//xmax').text)
            ymax = int(bndbox.find('.//ymax').text)

            """ 領域切り出し& ポジティブサンプリング """
            roi = BB(xmin, ymin, xmax-xmin, ymax-ymin).getRoi(image)
            for bb in Detect(roi).detectRegion():
                crop = bb.getRoi(roi)
                if not crop is None:
                    positive.append(cv2.resize(crop, output_size))
            """ 値札領域を黒塗り """
            image_copy[ymin:ymax, xmin:xmax, :] = 0
            mask[ymin:ymax, xmin:xmax] = 1

        """ネガディブサンプリング"""
        for bb in Detect(image_copy).detectRegion():
            crop = bb.getRoi(image)
            if not crop is None:
                negative.append(cv2.resize(crop, output_size))


        """ 背景からランダムで切り出し """
        for i in range(3000):
            crop = randomSample(image, mask, output_size[0])
            if not crop is None:
                negative.append(crop)

        """ データセット """
        positive = random.sample(positive, fx(len(positive), 1000))
        negative = random.sample(negative, fx(len(negative), 3000))
        data = positive + negative
        data = np.transpose(np.asarray(data, dtype=np.float32), [0, 3, 1, 2])
        data = data[:, [2, 1, 0], :, :] / 255.0

        """ positive : 1, negative : 0 """
        labels = np.asarray([], dtype=np.int32)
        labels = np.append(labels, np.asarray(np.ones([len(positive)], dtype=np.int32)))
        labels = np.append(labels, np.asarray(np.zeros([len(negative)], dtype=np.int32)))
            
        logging.info('  [positive : {} , negative : {}]'.format(len(positive), len(negative)))
            

        experiment_data = {'data': data,
                           'labels': labels}

        with open(join(root_dir, 'pkl', 'data_{}.pkl'.format(time)), 'wb') as output:
            six.moves.cPickle.dump(experiment_data, output, -1)
            
    print 'done'

    """ ends here """


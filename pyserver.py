import cv2
import requests 
import os
import json
import shutil
import numpy as np
import random
from flask import Flask, request, abort
from flask_cors import CORS
from align import AlignDlib
from model import create_model
import tensorflow as tf
from sklearn.manifold import TSNE
from sklearn.preprocessing import LabelEncoder
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import LinearSVC
import matplotlib.pyplot as plt
import pickle


app = Flask(__name__)

CORS(app, support_credentials=True)

graph = tf.get_default_graph()
nn4_small2_pretrained = create_model()
nn4_small2_pretrained.load_weights(os.path.join(os.getcwd() , 'weights/nn4.small2.v1.h5'))

def align_image(img):
    return alignment.align(96, img, alignment.getLargestFaceBoundingBox(img), 
                           landmarkIndices=AlignDlib.OUTER_EYES_AND_NOSE)

def align_image_bb(img,bb):
    return alignment.align(96, img, bb, 
                           landmarkIndices=AlignDlib.OUTER_EYES_AND_NOSE)

def load_image(path):
    img = cv2.imread(path, 1)
    return img[...,::-1]

alignment = AlignDlib(os.path.join(os.getcwd() , 'models/landmarks.dat'))

class IdentityMetadata():
    def __init__(self, base, name, file):
        # dataset base directory
        self.base = base
        # identity name
        self.name = name
        # image file name
        self.file = file

    def __repr__(self):
        return self.image_path()

    def image_path(self):
        return os.path.join(self.base, self.name, self.file) 
    
def load_metadata(path):
    metadata = []
    for i in os.listdir(path):
        for f in os.listdir(os.path.join(path, i)):
            metadata.append(IdentityMetadata(path, i, f))
    return np.array(metadata)


@app.route('/faceTrain/<user>', methods=['POST'])
def trainImage(user):
    path = os.path.join(os.getcwd() , "static" , user, "face")
    metadata = load_metadata(os.path.join(path , "images"))
    global graph
    global nn4_small2_pretrained
    embedded = np.zeros((metadata.shape[0], 128))
    for i, m in enumerate(metadata):
        img = load_image(m.image_path())
        try:
            img = align_image(img)
            img = (img / 255.).astype(np.float32)
            with graph.as_default():
                embedded[i] = nn4_small2_pretrained.predict(np.expand_dims(img, axis=0))[0]
        except:
            pass
        
    targets = np.array([m.name for m in metadata])
    X_embedded = TSNE(n_components=2).fit_transform(embedded)

    plt.clf()

    for i, t in enumerate(set(targets)):
        idx = targets == t
        plt.scatter(X_embedded[idx, 0], X_embedded[idx, 1], label=t)   

    plt.legend(bbox_to_anchor=(1, 1))
    plt.tight_layout()
    if not os.path.exists(os.path.join(path , 'test')):
        os.makedirs(os.path.join(path , 'test'))
    plt.savefig(os.path.join(path , 'test' , 'result.png'))
    try:
        os.remove(os.path.join(path , 'test' , 'embedded.pkl')
    except:
        print("doesnt exist")
    with open(os.path.join(path , 'test', 'embedded.pkl'), 'wb') as f:
        pickle.dump(embedded, f, pickle.HIGHEST_PROTOCOL)
    return "cleared",201

@app.route('/faceUpload', methods=['POST'])
def task():
    if 'file' not in request.files:
        abort(400)
    user = request.form.get('user')
    name = request.form.get('name')
    path = os.path.join(os.getcwd() , "static" , user , "face/images" , name)
    if not os.path.exists(path):
        os.makedirs(path)
    images = request.files.to_dict() #convert multidict to dict
    for image in request.files.getlist('file'):
        image.save(os.path.join(path, image.filename))

    return "done",201

@app.route('/faceGetImages/<user>', methods=['POST'])
def getImage(user):
    path = os.path.join(os.getcwd() , "static" , user , "face/images")
    files = {}
    for i in os.listdir(path):
        files[i] = []
        for f in os.listdir(os.path.join(path, i)):
            templist = files[i]
            templist.append(f)
            files[i] = templist 
    json_data = json.dumps(files)

    return json_data,201

@app.route('/faceClearImages/<user>', methods=['POST'])
def clearImage(user):
    path = os.path.join(os.getcwd() , "static" , user , "face")
    shutil.rmtree(path, ignore_errors=True)
    return "cleared",201


@app.route('/faceTest', methods=['POST'])
def testImage():
    user = request.form.get('user')
    path = os.path.join(os.getcwd(), "static" , user, "face")
    metadata = load_metadata(os.path.join(path , "images"))
    targets = np.array([m.name for m in metadata])
    with open((path+'/test/embedded.pkl'), 'rb') as f:
        embedded = pickle.load(f)
    encoder = LabelEncoder()
    encoder.fit(targets)
    y = encoder.transform(targets)
    svc = LinearSVC()
    svc.fit(embedded, y)
    global graph
    global nn4_small2_pretrained
    font = cv2.FONT_HERSHEY_SIMPLEX
    path = os.path.join(os.getcwd(), "static", user, "face", "test" , "result")
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    images = request.files.to_dict()
    for image in request.files.getlist('file'):
        image.save(os.path.join(path , image.filename))
        path1 = os.path.join(path, image.filename)
    frame = cv2.imread(path1, 1)
    bb = alignment.getAllFaceBoundingBoxes(frame)
    if bb is not None:
        for i in range(len(bb)):
            cv2.rectangle(frame, (bb[i].left(), bb[i].top()), (bb[i].left()+bb[i].width(), bb[i].top()+bb[i].height()), (255,0,0), 2)
            img = align_image_bb(frame,bb[i])
            if img is not None:
                img = (img / 255.).astype(np.float32)
                with graph.as_default():
                    embedding = nn4_small2_pretrained.predict(np.expand_dims(img, axis=0))[0] 
                prediction = svc.predict(embedding.reshape(1,-1))
                identity = encoder.inverse_transform(prediction)[0]
                cv2.putText(frame,identity,(bb[i].left(),bb[i].top()-10), font, 0.7,(0,0,255),2,cv2.LINE_AA)
    key = str(random.randint(1,1000000))
    cv2.imwrite(path + "/" + key + '.jpg', frame)
    os.remove(path1)
    return key,201




if __name__ == "__main__":
    app.run(host= '0.0.0.0')
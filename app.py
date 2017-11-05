from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, sys
from flaskext.mysql import MySQL


import warnings
import json
warnings.filterwarnings("ignore")

from dejavu import Dejavu
from dejavu.recognize import FileRecognizer, MicrophoneRecognizer



# DESCRIPTION : 
# 	This is the entrypoint of application. It handles following incoming requests:
#
#   > /upload/
#       POST request with 'file'(audioclip) and 'adcontent' at this endpoint, stores clip and its
#       Fingerprint and related AdContent to DB.
#    
#   > /match/
#       POST request containing sample audioclip at this point,
#       searches for OriginalClip and then returns the
#       related AdContent to API caller in json format, like:
#       {
#           "adcontent": "Zaalima CocaCola Pila Day !!!", 
#           "match_time": 2.169373035430908, 
#           "song_id": 1, 
#           "song_name": "Cocacola"
#       }
#


mysql = MySQL()
app = Flask(__name__)
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'blogger55'
app.config['MYSQL_DATABASE_DB'] = 'dejavu'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

UPLOAD_FOLDER = 'uploads/'
TEMP_FOLDER = 'temp/'
ALLOWED_EXTENSIONS = set(['mp3'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# load PyDejavuDB config from a JSON file (or anything outputting a python dictionary)
with open("dejavu.cnf.SAMPLE") as f:
    config = json.load(f)

@app.route('/upload/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        adcontent = request.form['adcontent']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            # Can also rename the uploaded file if you want
            #os.rename(UPLOAD_FOLDER + filename, UPLOAD_FOLDER+'niloofar.jpg')
            FILEPATH = UPLOAD_FOLDER + filename
            

            #Initializing Dejavu object with config
            djv = Dejavu(config)
            
            #Insert clip and its fingerprint in DB
            sid = djv.fingerprint_file(FILEPATH)

            #Insert related AdContent to DB
            # Create db connection to add data
            db = mysql.connect()
            cursor = db.cursor()
            cursor.execute("INSERT INTO adcontent (sid, content) VALUES (%s,%s)", (sid, adcontent))
            db.commit()
            db.close()

            #Data object for html template
            data={"sid":sid}            

            print ("\nSuccessfully added clip and adcontent to DB and recorded Fingerprint!")
            return render_template('upload.html', data=data)

    return render_template('upload.html')


def getAdContent(sid):

    #DB connection for getting adcontent related to 'sid'
    dbx = mysql.connect()
    c = dbx.cursor()
    adcontent = c.execute("SELECT * FROM adcontent WHERE sid=%s", (sid))
    adcontent = c.fetchone()
    
    return adcontent[2]


@app.route('/match', methods=['GET', 'POST'])
def match_file():
    
    if request.method == 'POST':
        print(str(request))
        file = request.files['uploaded_file']
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['TEMP_FOLDER'], filename))

            FILEPATH = TEMP_FOLDER + filename

            #Initializing Dejavu object with config
            djv = Dejavu(config)

            #Passing sample clip for retrieving the original track
            matched_track = djv.recognize(FileRecognizer, FILEPATH)
            print(matched_track)

            #Retrieve AdContent of the matched_track
            adcontent = getAdContent(matched_track['song_id'])

            response = {
                "song_id": matched_track['song_id'],
                "song_name": matched_track['song_name'],
                "match_time": matched_track['match_time'],
                "adcontent": adcontent
                }    
            
            #Delete temporary sample clip
            os.remove(FILEPATH)

            #Return response to API caller in JSON format
            return jsonify(response)
        
    return render_template('match.html')
    

@app.route('/')
def index():
      return '''
      <a href='upload'>Click to upload</a>
      '''

if __name__ == '__main__':
    app.run(host='0.0.0.0')

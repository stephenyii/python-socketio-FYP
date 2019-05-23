#!/usr/bin/env python
async_mode = None

import time
from flask import Flask, render_template
import socketio
import random
import pika

# USER_CONNECTED = False

sio = socketio.Server(logger=True, async_mode=async_mode)
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
app.config['SECRET_KEY'] = 'secret!'
thread = None

# start a connection with localhost
# credentials = pika.PlainCredentials('guest', 'guest')
# connection = pika.BlockingConnection(pika.ConnectionParameters('172.17.9.74', 5672, '/', credentials))
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

# more queue below, one queue per pi
first_queue_name = 'decibel_one'

# declare queue here
channel.queue_declare(queue=first_queue_name)

def randomNo():
	tmp = random.randint(1,101)
	return tmp

def callback(ch, method, properties, body):
    print('received message of', body)
    DECIBEL_DATA = body.decode()
    sio.emit('my response1', {'data': DECIBEL_DATA},
                 namespace='/test')
    sio.emit('my response2', {'data': randomNo()}, namespace='/test')

def background_thread():
    channel.basic_consume(callback,queue=first_queue_name,no_ack=True)
    channel.start_consuming()


@app.route('/')
def index():
    global thread
    if thread is None:
        thread = sio.start_background_task(background_thread)
    return render_template('index.html')

@sio.on('my event', namespace='/test')
def test_message(sid, message):
    sio.emit('my response', {'data': message['data']}, room=sid,
             namespace='/test')
    # prints i'm connected
    print('my event: ' + str(message['data']))
    # if (str(message['data']) == 'I\'m connected!'):
    #     USER_CONNECTED = True

@sio.on('connect', namespace='/test')
def test_connect(sid, environ):
    sio.emit('my response', {'data': 'Connected', 'count': 0}, room=sid,
             namespace='/test')


@sio.on('disconnect', namespace='/test')
def test_disconnect(sid):
    print('Client disconnected')


# We kick off our server
if __name__ == '__main__':
    if sio.async_mode == 'threading':
        # deploy with Werkzeug
        app.run(threaded=True)
    elif sio.async_mode == 'eventlet':
         # deploy with eventlet
        import eventlet
        import eventlet.wsgi
        eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
    elif sio.async_mode == 'gevent':
        # deploy with gevent
        from gevent import pywsgi
        try:
            from geventwebsocket.handler import WebSocketHandler
            websocket = True
        except ImportError:
            websocket = False
        if websocket:
            pywsgi.WSGIServer(('', 5000), app,
                              handler_class=WebSocketHandler).serve_forever()
        else:
            pywsgi.WSGIServer(('', 5000), app).serve_forever()
    elif sio.async_mode == 'gevent_uwsgi':
        print('Start the application through the uwsgi server. Example:')
        print('uwsgi --http :5000 --gevent 1000 --http-websockets --master '
              '--wsgi-file app.py --callable app')
    else:
        print('Unknown async_mode: ' + sio.async_mode)
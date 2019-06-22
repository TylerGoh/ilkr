const express = require('express')
const app = express()
const path = require('path');
const serv = require('http').Server(app);
const mongoose = require('mongoose');
var bodyParser = require('body-parser')
const cors = require('cors')
const url = `mongodb://@127.0.0.1:27017/coffeeshop?authSource=admin`;
var io = require('socket.io')(serv, {});


SOCKET_LIST = {};

mongoose.connect(url, {useNewUrlParser: true});
serv.listen(80);
app.use(cors());
app.use(bodyParser.json())
console.log("Server started.");

app.use('/static', express.static(__dirname + '/static'));

app.use(express.static(path.join(__dirname, 'build')));

app.get('/', function(req, res) {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

app.get('*', function (request, response){
    response.sendFile(path.resolve(__dirname, 'build', 'index.html'))
  })

app.post('/register', (req, response) => {
    data = req.body;
    if(data.name.length < 8 && data.password.length < 8)
    {
    response.send('invalid')
    return
    }
    isUsernameTaken(data, function (res) {
    if (res) {
        response.send('failure')
    } else {
        addUser(data, function () {
        response.send('success');
        });
    }
    });
})

app.post('/login', (req, response) => {
    data = req.body;
    if(data.name.length < 8 && data.password.length < 8)
    {
    response.send('invalid')
    return
    }
    isValidPassword(data, function (res) {
        if (res) {
            console.log("Sign in from " + data.name);
            response.send('success')
        } 
        else 
        {
            isUsernameTaken(data, function(check) {
                if(check)
                    response.send('wrongPass');
                else
                    response.send('wrongUser');
            })
        }
    });
})


app.post('/checkUsername', (req, response) => {
    data = req.body;
    isUsernameTaken(data, function (res) {
    if (res)
        response.send('failure')
    else 
        response.send('success');
    });
})




var isValidPassword = function (data, cb) {
    Account.find({ name:data.name, password:data.password }).then(doc => {
        console.log(doc)
        if (doc.length > 0)
            cb(true);
        else
            cb(false);})
};


var isUsernameTaken = function (data, cb) {
    Account.find({ name: data.name }).then(doc => {
        if (doc.length > 0)
            cb(true);
        else
            cb(false);})
};

var addUser = function (data, cb) {
    new Account({
        _id: new mongoose.Types.ObjectId(),
        name: data.name,
        password: data.password
    }).save();
    console.log("new account added")
    cb()
};


const accountSchema = mongoose.Schema({
    _id: mongoose.Schema.Types.ObjectId,
    name: String,
    password: String
})

const Account = mongoose.model('Account', accountSchema);
io.sockets.on('connection',(socket)=> {
    console.log("connection");
    socket.id = Math.random();
    SOCKET_LIST[socket.id] = socket;
    socket.emit('test', {result:"testy"})

    socket.on('disconnect', ()=> {
        delete SOCKET_LIST[socket.id];
        console.log(Object.keys(SOCKET_LIST).length);
    });

    socket.on('end', function() {
        socket.disconnect();
    });
});





const express = require('express');
const app = express();
const router = express.Router();

app.get('/users', getUsers);
app.post('/users', createUser);
app.delete('/users/:id', deleteUser);
app.put('/users/:id', updateUser);

router.get('/items', listItems);
router.post('/items', addItem);

function getUsers(req, res) { res.json([]); }
function createUser(req, res) { res.json({}); }
function deleteUser(req, res) { res.json({}); }
function updateUser(req, res) { res.json({}); }
function listItems(req, res) { res.json([]); }
function addItem(req, res) { res.json({}); }

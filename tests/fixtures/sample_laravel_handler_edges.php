<?php

use Illuminate\Support\Facades\Route;

class UserController {
    public function index() {}
    public function store() {}
}

class PostController {
    public function index() {}
    public function show() {}
    public function update() {}
    public function destroy() {}
}

Route::get('/users', 'UserController@index');
Route::post('/users', 'UserController@store');
Route::apiResource('posts', PostController::class)->only(['index', 'show', 'update', 'destroy']);
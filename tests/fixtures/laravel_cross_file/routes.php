<?php

use Illuminate\Support\Facades\Route;

Route::get('/users', 'UserController@index');
Route::apiResource('posts', PostController::class)->only(['show']);
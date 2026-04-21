<?php

use Illuminate\Support\Facades\Route;

Route::group(['prefix' => 'api'], function () {
    Route::get('/users', 'UserController@index');
    Route::post('/users', 'UserController@store');
});

Route::prefix('admin')->group(function () {
    Route::delete('/users/{id}', 'AdminUserController@destroy');
});

Route::resource('/posts', PostController::class);
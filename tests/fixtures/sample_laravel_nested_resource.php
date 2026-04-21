<?php

use Illuminate\Support\Facades\Route;

Route::resource('users.posts', PostController::class)->only(['index', 'show']);
Route::apiResource('teams.members', MemberController::class)->except(['destroy']);
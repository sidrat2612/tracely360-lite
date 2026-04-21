<?php

use Illuminate\Support\Facades\Route;

Route::resource('photos.comments', CommentController::class)->shallow()->only(['index', 'show', 'destroy']);
Route::apiResource('teams.members', MemberController::class)->except(['destroy'])->shallow();
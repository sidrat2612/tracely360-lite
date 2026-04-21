<?php

use Illuminate\Support\Facades\Route;

Route::apiResource('/comments', CommentController::class);
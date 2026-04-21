import { Controller, Get, Post } from '@nestjs/common';

@Controller('users')
class UserController {
  @Get()
  listUsers() {
    return [];
  }

  @Post(':id')
  createUser() {
    return {};
  }
}
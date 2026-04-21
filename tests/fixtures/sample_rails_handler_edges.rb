class UsersController
  def index
  end

  def show
  end
end

class PostsController
  def index
  end

  def show
  end

  def update
  end

  def destroy
  end
end

Rails.application.routes.draw do
  get 'users', to: 'users#index'
  get 'users/:id', to: 'users#show'
  resources :posts, only: [:index, :show, :update, :destroy]
end
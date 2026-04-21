Rails.application.routes.draw do
  namespace :admin do
    get 'users', to: 'users#index'
    resources :posts, only: [:show]
  end
end
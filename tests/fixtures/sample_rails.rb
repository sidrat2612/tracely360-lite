Rails.application.routes.draw do
  namespace :admin do
    get 'health'
    post 'login'
    resources :users
  end
end
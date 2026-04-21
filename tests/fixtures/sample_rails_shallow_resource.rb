Rails.application.routes.draw do
  namespace :admin do
    resources :articles do
      resources :comments, shallow: true, only: [:index, :show, :destroy] do
        resources :likes, only: [:index]
      end
    end
  end
end
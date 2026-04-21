Rails.application.routes.draw do
  namespace :admin do
    resource :profile
  end
end
from fastapi import APIRouter, FastAPI

app = FastAPI()
router = APIRouter(prefix='/items')


@router.get('/{item_id}')
def get_item(item_id: str):
    return {'id': item_id}


@router.post('')
def create_item():
    return {}, 201


app.include_router(router, prefix='/v1')
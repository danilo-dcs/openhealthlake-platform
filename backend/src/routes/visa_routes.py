

import traceback
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from services.VisasServices import VisaServices
from shared.models.visas import AssertedVisaModel, CreateVisaPayload, VisaModel

from routes.auth_routes import auth_oauth2_scheme

router = APIRouter(prefix="/visa", tags=["Passport Visas"])


@router.get("/list", summary="List Passport Visas", response_model=List[VisaModel])
async def list_all_visas(_: str = Depends(auth_oauth2_scheme)) -> List[VisaModel]:

    visaServices = VisaServices()

    response = await visaServices.list_all()

    return response


@router.get("/id/{visa_uuid}", summary="Get Passport Visa by Id", response_model=AssertedVisaModel)
async def get_visa_by_id(visa_uuid: str, _: str = Depends(auth_oauth2_scheme)) -> AssertedVisaModel:

    visaServices = VisaServices()

    response = await visaServices.get_by_id(visa_uuid=visa_uuid)

    return response


@router.post("/create", summary="Create Passport Visas", response_model=VisaModel)
async def create_visa(payload: CreateVisaPayload, _: str = Depends(auth_oauth2_scheme)) -> VisaModel:

    try:
        visaServices = VisaServices()

        response = await visaServices.create_visa(payload)

    except Exception as e:
        error_message = f"Error saving file: {str(e)}"
        stack_trace = traceback.format_exc()
        print("An error occurred:")
        print(stack_trace) 
        raise HTTPException(status_code=500, detail=error_message)  

    return response


@router.put("/update", summary="Create Passport Visas", response_model=VisaModel)
async def update_visa(payload: AssertedVisaModel, _: str = Depends(auth_oauth2_scheme)) -> VisaModel:

    try:
        visaServices = VisaServices()

        response = await visaServices.update_visa(payload)

    except Exception as e:
        error_message = f"Error saving file: {str(e)}"
        stack_trace = traceback.format_exc()
        print("An error occurred:")
        print(stack_trace) 
        raise HTTPException(status_code=500, detail=error_message)  

    return response


@router.delete("/delete/{visa_uuid}", summary="Delete Visas by Id")
async def delete_visa_by_id(visa_uuid: str, _: str = Depends(auth_oauth2_scheme)) -> JSONResponse:

    visaServices = VisaServices()

    response = await visaServices.delete_visa(visa_uuid=visa_uuid)

    return JSONResponse(content=f"Item deleted!\nDetails:  {str(response)}", status_code=200)
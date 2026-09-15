from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication as JSONWebTokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from pTracker.api.asset_management.purchase_order_biz import AssetBL
from pTracker.api.asset_management.vendor_biz import VendorBL
from pTracker.api.asset_management.asset_category_biz import AssetCategoryBL


class CreatePurchaseOrderView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self,request):
        response = AssetBL().create_or_update_purchase_order(request.data,request.user)
        return Response(response)


class UpdatePurchaseOrderView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self,request):
        response = AssetBL().create_or_update_purchase_order(request.data,request.user)
        return Response(response)


class GetPurchaseOrderView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self):
        response = AssetBL().get_all_purchase_order()
        return Response(response)


class PurchaseOrderApproval(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self,poID,request):
        response = AssetBL().purchase_order_approval(poID , request.user,request.data)
        return Response(response)
    
# class DeletePurchaseOrderView(APIView):
#     authentication_classes = [JSONWebTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self,request):
#         response = AssetBL().delete_purchase_order(request)
#         return Response(response)

class CreateVendorView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request):
        response = VendorBL().create_or_update_vendor(request.user.id,request.data)
        return Response(response)


class UpdateVendorView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self,request):
        response = VendorBL().create_or_update_vendor(request.user.id,request.data)
        return Response(response)


class GetAllVendorView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        response = VendorBL().get_all_vendor(request.user)
        return Response(response)


class DeleteVendorView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request,vendorID):
        response = VendorBL().delete_vendor(request.user,vendorID)
        return Response(response)


class CreateAssetCategoryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self, request):
        response = AssetCategoryBL().create_or_update_asset_category(request.user, request.data)
        return Response(response)


class UpdateAssetCategoryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser,FormParser,JSONParser)

    def post(self,request):
        response = AssetCategoryBL().create_or_update_asset_category(request.user, request.data)
        return Response(response)

class DeleteAssetCategoryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, categoryID):
        response = AssetCategoryBL().delete_asset_category(request.user, categoryID)
        return Response(response)

class GetAssetCategoryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        response = AssetCategoryBL().get_asset_category_all(request.user)
        return Response(response)

class GetParentAssetCategory(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self,request):
        response = AssetCategoryBL().get_parent_asset_category(request.user)
        return Response(response)


class GetSubCategoryView(APIView):
    authentication_classes = [JSONWebTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = AssetCategoryBL().get_sub_asset_category_by_parentID(request.user, request.data)
        return Response(response)





    
    















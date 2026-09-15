#wiki context processor

def user_group(request):
    try:
        user = request.session['user_group']
    except Exception as error:
        # print(repr(error))
        user = None
    return {'user_group': user}
# Create your views here.
from datetime import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect

from rango.models import Category, CategryLikes, Page, UserProfile
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from rango.bing_search import run_query
from url_encoding import *

def get_category_list(max_results=0, starts_with=''):
    cat_list = []
    if starts_with:
        cat_list = Category.objects.filter(name__startswith=starts_with).order_by('name')
    else:
        cat_list = Category.objects.all()

    if max_results > 0:
        if len(cat_list) > max_results:
            cat_list = cat_list[:max_results]

    for cat in cat_list:
        cat.url = encode_url(cat.name)

    return cat_list

def suggest_category(request):
    context = RequestContext(request)

    context_dict = init_context(request)
    cat_list = []
    starts_with = ''
    if request.GET.has_key('suggestion'):
        starts_with = request.GET['suggestion']

    cat_list = get_category_list(8,starts_with)
    context_dict['category_list'] = cat_list

    return render_to_response('rango/category_list.html',context_dict,context)

def count_visits(request):

    if request.session.get('last_visit'):
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits+1
            request.session['last_visit'] = str(datetime.now())
    else:
        visits = 0
        request.session['visits'] = visits + 1
        request.session['last_visit'] = str(datetime.now())
    print "visits = ",visits

def init_context(request):
    category_list = Category.objects.order_by('-likes')[:8]
    page_list = Page.objects.order_by('-views')[:5]

    for category in category_list:
        category.url = encode_url(category.name)

    context_dict = {'category_list':category_list,'page_list':page_list,'request':request}
    return context_dict

def index(request):
    context = RequestContext(request)
    
    context_dict = init_context(request) 

    if request.GET.has_key('error_message'):
        context_dict['error_message'] = request.GET['error_message'] 

    count_visits(request)

    return render_to_response('rango/index.html',context_dict,context)

def category(request, category_name_url):
    context = RequestContext(request)
    
    context_dict = init_context(request)

    category_name = decode_url(category_name_url)
    context_dict['category_name'] = category_name
    context_dict['category_url'] = category_name_url
    request.session['search_source'] = 'category'

    if request.session.get('category_url') != category_name_url:
        if request.session.get('result_list'):
            del request.session['result_list']
    request.session['category_url'] = category_name_url

    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category).order_by('-views')

        context_dict['pages'] = pages
        context_dict['category'] = category

        try:
            user_like = CategryLikes.objects.get(cat=category, user=request.user)
        except:
            user_like = None

        context_dict['user_like'] = user_like

        if request.session.get('result_list'):
            context_dict['result_list'] = request.session.get('result_list')

        return render_to_response('rango/category.html',context_dict, context)
    except Exception as e:
        return HttpResponseRedirect(reverse('rango:index')+"?error_message="+str(e))

def all_categories(request):
    context = RequestContext(request)

    context_dict = init_context(request)
    
    category_list = Category.objects.order_by('-likes')

    all_category_list = Category.objects.order_by('-likes')
    context_dict['all_categories'] = all_category_list
    for category in all_category_list:
        category.url = encode_url(category.name)

    return render_to_response('rango/all_categories.html', context_dict, context)

def about(request):
    context = RequestContext(request)
    
    context_dict = init_context(request)
    
    visits = 0
    if request.session.get('visits'):
        visits = request.session.get('visits')
    context_dict['aboutmessage'] = "This is a site popularity tracker that is serves to inform the users how popular a certain site is among Rango's users.  The more a link is clicked within the Rango application, the better it's score is.  If you'd like to add a new page or category, you can do so once you've registered with the app.  Have fun with Rango!"
    context_dict['visits'] = visits
        
    return render_to_response('rango/about.html',context_dict,context)

@login_required()
def add_category(request):
    context = RequestContext(request)

    context_dict = init_context(request)

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)

            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()

    context_dict['form'] = form

    return render_to_response('rango/add_category.html', context_dict,context)

@login_required()
def add_page(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_url(category_name_url)

    context_dict = init_context(request)

    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            page = form.save(commit=False)
            
            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html', context_dict, context)

            page.views = 0

            page.save()

            return category(request,category_name_url)
        else:
            print form.errors
    else:
        page_t = ""
        page_u = ""
        if request.GET.has_key('title'):
            page_t = request.GET['title']
        if request.GET.has_key('url'):
            page_u = request.GET['url']
        form = PageForm(initial={'title': page_t, 'url': page_u})
        context_dict['category_name_url'] = category_name_url
        context_dict['category_name'] = category_name
        context_dict['form'] = form

    return render_to_response('rango/add_page.html', context_dict, context)

@login_required()
def quick_add_page(request):
    context = RequestContext(request)
    context_dict = {}

    if request.GET.has_key('cat') and request.GET.has_key('url') and request.GET.has_key('title'):
        try:
            cat_id = Category.objects.get(name=decode_url(request.GET['cat']))
            try:
                page = Page.objects.get(title=request.GET['title'])
            except:
                new_page = Page(category=cat_id, title=request.GET['title'], url=request.GET['url'])
                new_page.save()
            context_dict['pages'] = Page.objects.filter(category=cat_id).order_by('-views')
        except Exception as e:
            print "Error:: ",e

    return render_to_response('rango/ajax/category_page_list.html',context_dict,context)

def register(request):
    context = RequestContext(request)

    context_dict = init_context(request)

    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()
            registered = True
    else:
       user_form = UserForm()
       profile_form = UserProfileForm()

    context_dict['user_form'] = user_form
    context_dict['profile_form'] = profile_form
    context_dict['registered'] = registered

    return render_to_response('rango/register.html',
        context_dict ,context)

def user_login(request):
    context = RequestContext(request)

    context_dict = init_context(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(request.POST['next'])
            else:
                error_message = 'Your Rango account is disabled'
        else:
            error_message = 'Invalid login details supplied'
        return HttpResponseRedirect('rango/login.html?error_message='+error_message)

    else:
        if 'error_message' in request.GET:
            context_dict['error_message'] = request.GET['error_message'] 
        if request.GET and request.GET.has_key('next'):
            context_dict['next_u'] = request.GET['next']
        else:
            context_dict['next_u'] = reverse('rango:index')
        print context_dict
        return render_to_response('rango/login.html',context_dict,context)

@login_required
def user_logout(request):
    logout(request)

    if request.GET.has_key('next'):
        return HttpResponseRedirect(request.GET['next'])
    else:
        return HttpResponseRedirect(reverse('rango:index'))

def search(request):
    context = RequestContext(request)

    context_dict = init_context(request)

    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)

    request.session['result_list'] = result_list

    if request.session.get('search_source'):
        search_source = request.session.get('search_source')
        if search_source == 'category':
            category_url = request.session.get('category_url')
            return redirect('rango:category',category_url)
        else:
            print "Not category"
    else:
        print "No Search Source"
    return redirect('rango:index')

def profile(request, uName):
    context = RequestContext(request)
    
    context_dict = init_context(request)
    
    try:
        this_user = User.objects.get(username=uName)
        this_profile = UserProfile.objects.get(user=this_user)
        context_dict['this_user'] = this_profile
        return render_to_response('rango/profile.html', context_dict, context)
    except:
        return redirect('rango:index')

def track_url(request, page_num):
    try:
        page = Page.objects.get(pk=page_num)

        page.views += 1
        page.save()

        return redirect(page.url)
    except:
        return redirect(reverse('rango:index')+'?error_message=Invalid Page')

@login_required
def like_category(request):
    context = RequestContext(request)
    cat_id = None
    context_dict = {}

    if request.GET.has_key('category_id'):
        cat_id = request.GET['category_id']
    
    likes = 0
    if cat_id:
        category = Category.objects.get(pk=int(cat_id))
        context_dict['category'] = category
        if category:
            try:
                user_like = CategryLikes.objects.get(cat=category, user=request.user)
                user_like.delete()
                likes = category.likes - 1
                context_dict['user_like'] = None
            except CategryLikes.DoesNotExist:
                new_like = CategryLikes(cat=category, user=request.user)
                new_like.save()
                likes = category.likes + 1
                context_dict['user_like'] = new_like
            category.likes = likes
            category.save()

    return render_to_response('rango/ajax/cat-like-div.html', context_dict, context)

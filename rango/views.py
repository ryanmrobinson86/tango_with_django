# Create your views here.
from datetime import datetime

from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response

from rango.models import Category, Page
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from url_encoding import *

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

def index(request):
    context = RequestContext(request)
    
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories':category_list,'pages':page_list}

    if 'error_message' in request.GET:
        context_dict['error_message'] = request.GET['error_message'] 
    
    for category in category_list:
        category.url = encode_url(category.name)

    count_visits(request)
    
    return render_to_response('rango/index.html',context_dict,context)

def category(request, category_name_url):
    context = RequestContext(request)

    category_name = decode_url(category_name_url)
    context_dict = {'category_name': category_name,'category_url':category_name_url}

    #try:
    category = Category.objects.get(name=category_name)
    pages = Page.objects.filter(category=category)

    context_dict['pages'] = pages
    context_dict['category'] = category
    return render_to_response('rango/category.html',context_dict, context)
    #except:
    #    return HttpResponseRedirect(reverse('rango:index'))

def about(request):
    context = RequestContext(request)
    
    visits = 0
    if request.session.get('visits'):
        visits = request.session.get('visits')
    context_dict = {
        'aboutmessage':"The about page is served from the context",
        'visits':visits
        }
    return render_to_response('rango/about.html',context_dict,context)

@login_required()
def add_category(request):
    context = RequestContext(request)

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)

            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()

    return render_to_response('rango/add_category.html', {'form': form},context)

@login_required()
def add_page(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_url(category_name_url)

    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            page = form.save(commit=False)
            
            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html', {}, context)

            page.views = 0

            page.save()

            return category(request,category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()

    return render_to_response('rango/add_page.html',
        {'category_name_url':category_name_url,
         'category_name':category_name,
         'form':form
        }, context)

def register(request):
    context = RequestContext(request)

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

    return render_to_response('rango/register.html',
        {'user_form':user_form,
         'profile_form':profile_form,
         'registered':registered
        },context)

def user_login(request):
    context = RequestContext(request)

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
        return HttpResponseRedirect(reverse('rango:index')+'?error_message='+error_message)

    else:
        context_dict = {}
        if request.GET and request.GET['next']:
            context_dict = {'next_u':request.GET['next']}
        else:
            context_dict = {'next_u':reverse('rango:index')}
        return render_to_response('rango/login.html',context_dict,context)

@login_required
def user_logout(request):
    logout(request)

    return HttpResponseRedirect(reverse('rango:index'))

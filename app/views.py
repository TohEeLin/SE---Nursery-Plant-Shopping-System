import re
from django.db.models import Sum, Q
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout as django_logout, get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .models import DeliveryMan, Plant, Order, Review,ShoppingCart,CartItem,WishlistItem,Wishlist,OrderItem,Payment,Customer,User
from django.db import transaction
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.validators import validate_email, RegexValidator
from django.core.exceptions import ValidationError

def home(request):
    plant_objects = Plant.objects.all()
    for plant in plant_objects:
        plant.reviews = Review.objects.filter(order_item__plant=plant)

    item_name = request.GET.get('item_name')
    if item_name:
        plant_objects = plant_objects.filter(plant_name__icontains=item_name)
        if not plant_objects:
            message = "No matching plants found."
            context = {'message': message}
            return render(request, 'index.html', context)

    context = {'plant_objects': plant_objects}
    return render(request, "index.html", {'plant_objects': plant_objects, 'item_name': item_name})

# General
# by TEO YU JIE
def loginPage(request):
    messages = None # Initial
    if request.method == 'POST':
        user_email = request.POST.get('email')
        user_password = request.POST.get('password')
        user = authenticate(request, email=user_email, password=user_password)
        if user is not None:
            login(request, user)
            # Redirect to different dashboards based on the user's role
            if user.is_admin:
                request.session['user_email'] = user.email # Determine user
                return redirect('adminDashboard') 
             
            elif user.is_deliveryman:
                request.session['user_email'] = user.email
                return redirect('deliveryDashboard')
            
            elif user.is_customer:
                request.session['user_email'] = user.email
                return redirect('customer_dashboard')  # Replace with with customer de URL
            
            else:
                messages = "You do not have the permission to login."

        else:
            messages = "Invalid email or password."

    return render(request, 'login.html', {"messages": messages})

# by TEO YU JIE
UserModel = get_user_model()
def registrationPage(request):
    request.session['show_alert'] = False # After successfully registered, will show message

    if request.method == 'POST':
        full_name = request.POST.get('fullName')
        password = request.POST.get('password')
        email = request.POST.get('email')
        address = request.POST.get('address')
        state = request.POST.get('state')
        ic_number = request.POST.get('icNumber')
        phone_number = request.POST.get('phoneNumber')
        role = request.POST.get('role')
        
        try:
            with transaction.atomic():                
                user = UserModel.objects.create(
                    username=email.split('@')[0],  # for username
                    email=email,
                    is_customer=(role == 'customer'),
                    is_deliveryman=(role == 'delivery_man')
                )

                user.set_password(password)
                user.save()

                # after successful registration Yayyyyyy
                # Depending on the role, create the profile
                if role == 'customer':
                
                    Customer.objects.create( # Save inside customer table
                        user=user,
                        customer_name=full_name,
                        customer_address=address,
                        customer_state=state,
                        customer_ic=ic_number,
                        customer_phone_number=phone_number
                    )

                    login(request, user)
                    request.session['user_email'] = user.email
                    request.session['show_alert'] = True
                    return redirect('customer_dashboard') 

                elif role == 'delivery_man':
                    
                    DeliveryMan.objects.create( # Save inside delivery man table
                        user=user,
                        deliveryman_name=full_name,
                        deliveryman_address=address,
                        deliveryman_state=state,
                        deliveryman_ic=ic_number,
                        deliveryman_phone_number=phone_number
                    )

                    # login(request, user)
                    request.session['user_email'] = user.email
                    request.session['show_alert'] = True
                    return redirect('deliveryDashboard')
                
                else:
                    invalid_messages = 'Invalid role selected.'
                    return render(request, 'register.html', {'messages': invalid_messages})
        
        except Exception as e:
            # If any error occurs during the user creation, roll back the transaction.
            messages.error(request, f'An error occurred: {e}')
            return render(request, 'register.html')

    # If it's not a POST request or something went wrong, display the registration form again
    return render(request, 'register.html')

#by TEO YU JIE
def accountSetting(request):
    user_email = request.session.get('user_email')
    show_alert = request.session.get('show_alert')
    request.session['show_alert'] = False
    if user_email:
        try:
            user = None
            # User = delivery man, go delivery man db to check
            if User.objects.get(email = user_email).is_deliveryman:
                user = DeliveryMan.objects.get(user = User.objects.get(email = user_email))
                context = {
                    'full_name': user.deliveryman_name,
                    'email': user_email,
                    'address': user.deliveryman_address,
                    'state': user.deliveryman_state,
                    'ic': user.deliveryman_ic,
                    'phone': user.deliveryman_phone_number,
                    'show_alert': show_alert
                }

            # User = customer, go customer db to check
            elif User.objects.get(email = user_email).is_customer:
                user = Customer.objects.get(user = User.objects.get(email = user_email))
                context = {
                    'full_name': user.customer_name,
                    'email': user_email,
                    'address': user.customer_address,
                    'state': user.customer_state,
                    'ic': user.customer_ic,
                    'phone': user.customer_phone_number,
                    'show_alert': show_alert
                }

            # Cant find user
            elif user is None:
                return redirect('loginPage')
 
            return render(request, 'accountSetting.html', context)
        
        except Customer.DoesNotExist or DeliveryMan.DoesNotExist: #If user not found
            messages.error(request, 'User does not exist')
            return redirect('loginPage')
    else:
        return redirect('loginPage') #Just back to login page

# by TEO YU JIE
UserModel = get_user_model()
def editProfile(request):
    user_email = request.session.get('user_email')
    alert = request.session.get('alert')
    request.session['alert'] = False
    if user_email:
        try:
            if User.objects.get(email=user_email).is_deliveryman: # Delivery man's edit profile
                deliveryman = DeliveryMan.objects.get(user = User.objects.get(email=user_email))
                context = {
                    'full_name': deliveryman.deliveryman_name,
                    'email': user_email,
                    'address': deliveryman.deliveryman_address,
                    'state': deliveryman.deliveryman_state,
                    'ic': deliveryman.deliveryman_ic,
                    'phone': deliveryman.deliveryman_phone_number,
                    'alert': alert,
                }

                if request.method == 'POST':
                    name = request.POST.get('name')
                    email = request.POST.get('email')
                    phone = request.POST.get('phone')
                    address = request.POST.get('address')
                    state = request.POST.get('state')
                    ic = request.POST.get('ic')
                    with transaction.atomic():
                        # Update DeliveryMan details
                        deliveryman.deliveryman_name = name
                        deliveryman.deliveryman_address = address
                        deliveryman.deliveryman_state = state
                        deliveryman.deliveryman_ic = ic
                        deliveryman.deliveryman_phone_number = phone
                        deliveryman.save()
                        context['update_success'] = True

                        # Update User email
                        user = UserModel.objects.get(email=user_email)
                        user.email = email
                        user.save()
                        request.session['user_email'] = email
                    
                    request.session['alert'] = True
                    return redirect('editProfile')

                return render(request, 'editProfile.html', context)
                
            elif User.objects.get(email=user_email).is_customer: # Customers's edit profile
                customer = Customer.objects.get(user = User.objects.get(email=user_email))
                context = {
                    'full_name': customer.customer_name,
                    'email': user_email,
                    'address': customer.customer_address,
                    'state': customer.customer_state,
                    'ic': customer.customer_ic,
                    'phone': customer.customer_phone_number,
                    'alert': alert,
                }

                if request.method == 'POST':
                    name = request.POST.get('name')
                    email = request.POST.get('email')
                    phone = request.POST.get('phone')
                    address = request.POST.get('address')
                    state = request.POST.get('state')
                    ic = request.POST.get('ic')
                    with transaction.atomic():
                        # Update Customer details
                        customer.customer_name = name
                        customer.customer_address = address
                        customer.customer_state = state
                        customer.customer_ic = ic
                        customer.customer_phone_number = phone
                        customer.save()
                        context['update_success'] = True

                        # Update User email
                        user = UserModel.objects.get(email=user_email)
                        user.email = email
                        user.save()
                        request.session['user_email'] = email

                    request.session['alert'] = True
                    return redirect('editProfile')

                return render(request, 'editProfile.html', context)

        except DeliveryMan.DoesNotExist:
            messages.error(request, 'User does not exist')
            return redirect('loginPage')

    else:
        return redirect('loginPage')

# by TEO YU JIE
def changePassword(request):
    user_email = request.session.get('user_email')
    request.session['show_alert'] = False
    if user_email:

        if request.method == 'POST':
            password = request.POST.get('currentPassword')
            passwordNew = request.POST.get('newPassword')

            if (password == passwordNew):
                messages = 'New password cannot be the same as current password'
                return render(request, 'changePassword.html',{'messages': messages})

            user = authenticate(request, email = user_email, password = password)
            if user is not None:
                user.set_password(passwordNew)
                user.save()
                request.session['show_alert'] = True
                return redirect('accountSetting')
            else:
                messages = 'Invalid current password'
                return render(request, 'changePassword.html',{'messages': messages})

        return render(request, 'changePassword.html')
    else:
        return redirect('loginPage') # Back to login page

# Administrator
# by TOH EE LIN  
@user_passes_test(lambda user: user.is_admin)
def adminDashboard(request):
    return render(request, "admin_dashboard.html")

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def plantManagement(request):
    search_query = request.GET.get('search_query', '')   # Get search query from GET parameters, default to empty string
    error_message = None

    if search_query:
        plants = Plant.objects.filter(plant_name__icontains=search_query)
        
        if not plants.exists():
            error_message = "No matching plants are found."
    else:
        plants = Plant.objects.all()
    
    # Iterate over each plant and retrieve associated reviews
    for plant in plants:
        plant.reviews = Review.objects.filter(order_item__plant=plant)

    return render(request, "plant_management.html", {"plants": plants, "error_message": error_message}) 

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def createPlant(request):
    error_message = None
    if request.method == 'POST':
        plant_name = request.POST.get('plant_name')
        plant_description = request.POST.get('plant_description')
        plant_price = request.POST.get('plant_price')
        plant_availability = request.POST.get('plant_availability')
        plant_image = request.FILES.get('plant_image')

        # Regex for checking if the plant name contains only letters and spaces
        valid_name_pattern = re.compile(r"^[A-Za-z\s]+$")

        if not plant_image:
            error_message = 'You must upload a plant image.'
        elif not valid_name_pattern.match(plant_name):
            error_message = 'Plant name must only contain letters and spaces, and cannot be only numbers or special characters.'
        elif Plant.objects.filter(plant_name__iexact=plant_name).exists():
            error_message = 'A plant with this name already exists in the system.'
        else:
            try:
                plant_price = float(plant_price)
                if plant_price <= 0:
                    raise ValueError('Plant price must be greater than zero.')

                plant_availability = int(plant_availability)
                if plant_availability <= 0:
                    raise ValueError('Plant quantity must be greater than zero.')

                Plant.objects.create(
                    plant_name=plant_name,
                    plant_description=plant_description,
                    plant_price=plant_price,
                    plant_availability=plant_availability,
                    plant_image=plant_image
                )
                messages.success(request, 'The plant was successfully created.')
                return redirect('plantManagement')

            except ValueError as e:
                error_message = str(e)

        plants = Plant.objects.all()
        return render(request, "create_plant.html", {'plants': plants, 'error_message': error_message})

    plants = Plant.objects.all()
    return render(request, "create_plant.html", {'plants': plants, 'error_message': error_message})

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def updatePlant(request, plant_id):
    plant = get_object_or_404(Plant, pk=plant_id)
    error_message = None

    if request.method == 'POST':
        new_plant_name = request.POST.get('plant_name')
        new_plant_price = request.POST.get('plant_price')

        valid_name_pattern = re.compile(r"^[A-Za-z\s]+$")

        if not valid_name_pattern.match(new_plant_name):
            error_message = 'Plant name must only contain letters and spaces, and cannot be only numbers or special characters.'
        elif Plant.objects.filter(plant_name__iexact=new_plant_name).exclude(pk=plant_id).exists():
            error_message = 'A plant with this name already exists in the system.'
        elif float(new_plant_price) <= 0:
            error_message = 'Plant price must be greater than zero.'
        else:
            plant.plant_name = new_plant_name
            plant.plant_description = request.POST.get('plant_description')
            plant.plant_price = new_plant_price
            plant.plant_availability = request.POST.get('plant_availability')
            plant_image = request.FILES.get('plant_image')
            if plant_image:
                plant.plant_image = plant_image
            plant.save()

            messages.success(request, 'The plant was successfully updated.')
            return redirect('plantManagement')

    return render(request, 'update_plant.html', {'plant': plant, 'error_message': error_message})

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def deletePlant(request, plant_id):
    plant = get_object_or_404(Plant, id=plant_id)   # This ensures the plant exists, or returns a 404 error
    plant.delete()
    messages.add_message(request, messages.SUCCESS, 'The plant has been deleted.') 
    return redirect('plantManagement')

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def orderManagement(request):
    search_query = request.GET.get('search_query', '')
    error_message = None
    info_message = None  

    orders = (
        Order.objects
        .select_related('customer')
        .prefetch_related('order_items')
        .annotate(total_plant_quantity=Sum('order_items__plant_quantity'))
        .exclude(
            Q(payment__receive_method='Pickup', order_status='Completed') |
            Q(payment__receive_method='Delivery', order_status='Ready') |
            Q(payment__receive_method='Delivery', order_status='Out Of Delivery') |
            Q(payment__receive_method='Delivery', order_status='Completed')
        )
    )

    if search_query:
        try:
            search_query = int(search_query)
            orders = orders.filter(id=search_query)

            if not orders.exists():
                error_message = "No ongoing orders matched the entered order ID."

        except ValueError:
            error_message = "Invalid input. Please enter a numeric order ID."
            orders = Order.objects.none()
    else:
        # Check if there are no ongoing orders
        if not orders.exists():
            info_message = "There are no ongoing orders in the system."

    return render(request, "order_management.html", {"orders": orders, "error_message": error_message, "info_message": info_message})

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        order.order_status = request.POST.get('status')
        order.save()
        return redirect('orderManagement')  

    return redirect('orderManagement')

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def deliveryManagement(request):
    search_query = request.GET.get('search_query', '')
    error_message = None
    info_message = None  

    delivery_orders = (
        Order.objects
        .filter(payment__receive_method='Delivery', delman__isnull=True, order_status='Ready')
        .select_related('customer', 'payment')
        .prefetch_related('order_items')
    )

    deliverymen = DeliveryMan.objects.all()

    if search_query:
        try:
            search_query = int(search_query)
            delivery_orders = delivery_orders.filter(id=search_query)

            if not delivery_orders.exists():
                error_message = "No ongoing delivery orders matched the entered order ID."

        except ValueError:
            error_message = "Invalid input. Please enter a numeric order ID."
            delivery_orders = Order.objects.none()
    else:
        # Check if there are no ongoing delivery orders
        if not delivery_orders.exists():
            info_message = "There are no ongoing delivery orders in the system."

    return render(request, 'delivery_management.html', {'delivery_orders': delivery_orders, 'deliverymen': deliverymen, 'error_message': error_message, 'info_message': info_message})

# by TOH EE LIN
@user_passes_test(lambda user: user.is_admin)
def assign_delivery(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        deliveryman_id = request.POST.get('deliveryman')
        deliveryman = get_object_or_404(DeliveryMan, user_id=deliveryman_id)
        
        order.delman = deliveryman
        order.save()
        return redirect('deliveryManagement')
    
    return redirect('deliveryManagement')

# Delivery man
def deliveryDashboard(request): 
    user_email = request.session.get('user_email')
    show_alert = request.session.get('show_alert')
    request.session['show_alert'] = False
    if user_email:
        try:
            user = DeliveryMan.objects.get(user = User.objects.get(email = user_email))
            context = {
                'full_name': user.deliveryman_name,
                'email': user_email,
                'address': user.deliveryman_address,
                'state': user.deliveryman_state,
                'ic': user.deliveryman_ic,
                'phone': user.deliveryman_phone_number,
                'show_alert': show_alert
            }
            return render(request, 'deliveryDashboard.html', context)
        
        except DeliveryMan.DoesNotExist: #If user not found
            messages.error(request, 'User does not exist')
            return redirect('loginPage')
    else:
        return redirect('loginPage') # Back to login page

def pendingOrder(request):
    user_email = request.session.get('user_email')
    if user_email:
        try:
            user = DeliveryMan.objects.get(user=User.objects.get(email=user_email))
            delivery_orders = Order.objects.filter(delman=user, order_status='Ready')

            no_orders = delivery_orders.count() == 0

            if request.method == 'POST':
                action = request.POST.get('action')
                order_id = request.POST.get('orderId')

                if action == 'accept':
                    orders = Order.objects.filter(delman=user, id=order_id)
                    orders.update(order_status="Out Of Delivery")
                    return redirect('pendingOrder')
                
                elif action == 'reject':
                    orders = Order.objects.filter(delman=user, id=order_id)
                    orders.update(delman=None)
                    return redirect('pendingOrder')

            return render(request, "pendingOrder.html", {"delivery_orders": delivery_orders, "no_orders": no_orders})

        except DeliveryMan.DoesNotExist: 
            return redirect('loginPage')
    else:
        return redirect('loginPage')

def acceptedDelivery(request):
    user_email = request.session.get('user_email')
    if user_email:
        try:
            user = DeliveryMan.objects.get(user=User.objects.get(email=user_email))
            delivery_orders = Order.objects.filter(delman=user, order_status='Out Of Delivery')

            no_orders = delivery_orders.count() == 0

            if request.method == 'POST':
                action = request.POST.get('action')
                order_id = request.POST.get('orderId')

                if action == 'confirm':
                    orders = Order.objects.filter(delman=user, id=order_id)
                    orders.update(order_status="Completed")
                    return redirect('acceptedDelivery')
                
            return render(request, "acceptedDelivery.html", {"delivery_orders": delivery_orders, "no_orders": no_orders})

        except DeliveryMan.DoesNotExist: 
            return redirect('loginPage')
    else:
        return redirect('loginPage')

# Logout
def logout(request):
    django_logout(request)
    return redirect(home)

# Check data
def check_existing_data(request):
    if request.method == 'GET':
        full_name = request.GET.get('fullName')
        ic_number = request.GET.get('icNumber')
        email = request.GET.get('email')
        role = request.GET.get('role')

        exists_name = False
        exists_ic = False
        exists_email = False

        if role == 'customer':
            exists_name = Customer.objects.filter(customer_name=full_name).exists()
            exists_ic = Customer.objects.filter(customer_ic=ic_number).exists()
        elif role == 'delivery_man':
            # Adjust this part based on your model for delivery man
            exists_name = DeliveryMan.objects.filter(deliveryman_name=full_name).exists()
            exists_ic = DeliveryMan.objects.filter(deliveryman_ic=ic_number).exists()

        exists_email = User.objects.filter(email=email).exists()

        return JsonResponse({
            'exists': exists_name or exists_ic or exists_email,
            'exists_name': exists_name,
            'exists_ic': exists_ic,
            'exists_email': exists_email
        })

def check_existing_data_editProfile(request):
    if request.method == 'GET':
        full_name = request.GET.get('fullName')
        ic_number = request.GET.get('icNumber')
        email = request.GET.get('email')
        role = request.GET.get('role')
        user_email = request.session.get('user_email')

        exists_name = False
        exists_ic = False
        exists_email = False
        user = User.objects.get(email=user_email)
        if role == 'customer':
            
            customer = Customer.objects.get(user=user)
            exists_name = Customer.objects.filter(customer_name=full_name).exclude(id=customer.id).exists()
            exists_ic = Customer.objects.filter(customer_ic=ic_number).exclude(id=customer.id).exists()
        elif role == 'delivery_man':
            # Adjust this part based on your model for delivery man
            deliveryman = DeliveryMan.objects.get(user=user)
            exists_name = DeliveryMan.objects.filter(deliveryman_name=full_name).exclude(id=deliveryman.id).exists()
            exists_ic = DeliveryMan.objects.filter(deliveryman_ic=ic_number).exclude(id=deliveryman.id).exists()

        exists_email = User.objects.filter(email=email).exists()

        return JsonResponse({
            'exists': exists_name or exists_ic or exists_email,
            'exists_name': exists_name,
            'exists_ic': exists_ic,
            'exists_email': exists_email
        })
    
def customer_dashboard(request):
    if not request.user.is_authenticated:
        # Redirect to login page or display message if user not logged in
        messages.error(request, 'You must be logged in to view this page.')
        return redirect('loginPage')
    
    try:
        # Assuming that you have a `customer_profile` related_name set in your Customer model
        customer_profile = request.user.customer_profile
        full_name = customer_profile.customer_name
    except Customer.DoesNotExist:
        # If the customer profile does not exist, handle it appropriately
        messages.error(request, 'Customer profile not found.')
        return redirect('loginPage')

    plant_objects = Plant.objects.all()
    for plant in plant_objects:
        plant.reviews = Review.objects.filter(order_item__plant=plant)

    item_name = request.GET.get('item_name')
    message = None
    if item_name:
        plant_objects = plant_objects.filter(plant_name__icontains=item_name)
        if not plant_objects:
            message = "No matching plants found."

    show_success_message = request.session.pop('show_alert', False)  # Get and remove 'show_alert' from session

    context = {
        'plant_objects': plant_objects,
        'full_name': full_name,
        'show_success_message': show_success_message,
        'message': message,  # This is for the no matching plants found message
    }

    return render(request, 'customer_dashboard.html', context)

def plant_list_view(request):
    plant_objects = Plant.objects.all()
    for plant in plant_objects:
        plant.reviews = Review.objects.filter(order_item__plant=plant)

    item_name = request.GET.get('item_name')
    if item_name:
        plant_objects = plant_objects.filter(plant_name__icontains=item_name)
        if not plant_objects:
            message = "No matching plants found."
            context = {'message': message}
            return render(request, 'plant_list.html', context)

    context = {'plant_objects': plant_objects}
    return render(request, 'plant_list.html', context)

@login_required(login_url='registrationPage')
def add_to_cart(request, plant_id):
    # Check if the user has a customer profile
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must have a customer profile to add items to the cart.')
        return redirect('registrationPage')
    # Default the quantity to 1
    quantity = 1
    plant = get_object_or_404(Plant, id=plant_id)

    if plant.plant_availability < quantity:
        messages.error(request, f'Not enough {plant.plant_name} in stock.')
        return redirect('plant_list')
    
    customer = request.user.customer_profile
    cart, created = ShoppingCart.objects.get_or_create(customer=customer, defaults={'cart_total_price': 0})
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        plant=plant,
        defaults={'cart_plant_quantity': quantity, 'cart_item_price': plant.plant_price}
    )
    if not created:
        # If the item is already in the cart, don't change the quantity
        pass

    messages.success(request, f'{plant.plant_name} has been added to your cart.')
    return redirect('view_cart')


@login_required
def view_cart(request):
    customer = request.user.customer_profile
    try:
        cart = ShoppingCart.objects.get(customer=customer)
        items = CartItem.objects.filter(cart=cart)
        total_price = cart.get_total_cart_price()
    except ShoppingCart.DoesNotExist:
        items = []
        total_price = 0
    return render(request, 'cart.html', {'cart_items': items, 'total_price': total_price})



@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    item.delete()
    return HttpResponseRedirect(reverse('view_cart'))

@login_required
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            item.cart_plant_quantity = quantity
            item.save()
        else:
            item.delete()  # If the quantity is 0, remove the item
    return HttpResponseRedirect(reverse('view_cart'))

@login_required
def view_wishlist(request):
    customer = request.user.customer_profile
    wishlist_items = WishlistItem.objects.filter(wishlist__customer=customer)
    return render(request, 'wishlist.html', {'wishlist_items': wishlist_items})

@login_required(login_url='registrationPage')
def add_to_wishlist(request, plant_id):
    # Check if the user has a customer profile
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must have a customer profile to add items to the wishlist.')
        return redirect('registrationPage')  # Redirect to the registration page

    plant = get_object_or_404(Plant, id=plant_id)
    customer = request.user.customer_profile
    wishlist, created = Wishlist.objects.get_or_create(customer=customer)
    WishlistItem.objects.get_or_create(wishlist=wishlist, plant=plant)

    messages.success(request, f'{plant.plant_name} has been added to your wishlist.')
    return redirect('view_wishlist')

@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(WishlistItem, id=item_id)
    if item.wishlist.customer == request.user.customer_profile:
        item.delete()
    return redirect('view_wishlist')

@login_required
def to_review(request):
    customer = request.user.customer_profile
    # Get all order items to review for this customer that have not been reviewed yet
    order_items_to_review = OrderItem.objects.filter(
        order__customer=customer,
        to_review=True, 
        order__order_status='Completed'
    ).select_related('plant')

    # Create a set to keep track of which plants have been added
    plants_reviewed = set()
    unique_order_items_to_review = []

    for item in order_items_to_review:
        if item.plant not in plants_reviewed:
            unique_order_items_to_review.append(item)
            plants_reviewed.add(item.plant)

    return render(request, 'to_review.html', {'order_items_to_review': unique_order_items_to_review})


@login_required
def submit_review(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id, to_review=True)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        if rating:
            Review.objects.create(
                order_item=order_item,
                rating=rating,
                comment=comment
            )
            # Mark all order items of this plant as reviewed
            OrderItem.objects.filter(
                order__customer=order_item.order.customer,
                plant=order_item.plant,
                to_review=True
            ).update(to_review=False)
            messages.success(request, 'Your review has been submitted.')
            return redirect('to_review')
        else:
            messages.error(request, 'Rating is required.')
    return render(request, 'submit_review.html', {'order_item': order_item})


@login_required
def checkout(request):
    customer = request.user.customer_profile
    cart = ShoppingCart.objects.get(customer=customer)
    items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.plant.plant_price * item.cart_plant_quantity for item in items)
    
    if request.method == 'POST':
        receive_method = request.POST.get('receive_method')
        request.session['receive_method'] = receive_method  # Save the choice in the session
        if receive_method == 'Pickup':
            return redirect('make_payment')
        elif receive_method == 'Delivery':
            return redirect('delivery_details')
    
    # Pass the pickup and delivery options to the template
    context = {
        'cart_items': items,
        'total_price': total_price,
        'customer': customer
    }
    return render(request, 'checkout.html', context)


@login_required
def delivery_details(request):
    customer = request.user.customer_profile
    
    # Set shipping fee based on the customer's state
    if customer.customer_state in ['Sabah', 'Sarawak']:
        shipping_fee = Decimal('12.00')
    else:
        shipping_fee = Decimal('7.00')
    
    cart = ShoppingCart.objects.get(customer=customer)
    items = CartItem.objects.filter(cart=cart)
    plant_price = sum(item.plant.plant_price * item.cart_plant_quantity for item in items)
    total_price = plant_price + shipping_fee
    
    if request.method == 'POST':
        # Handle the order creation and payment process here
        # ...
        return redirect('make_payment')
    
    context = {
        'customer_name': customer.customer_name,
        'delivery_address': customer.customer_address,
        'plant_price': plant_price,
        'shipping_fee': shipping_fee,
        'total_price': total_price,
    }
    return render(request, 'delivery_details.html', context)

@login_required
def make_payment(request):
    customer = request.user.customer_profile
    cart = ShoppingCart.objects.get(customer=customer)
    items = CartItem.objects.filter(cart=cart)
    
    # Calculate the total cost of the plants in the cart
    plant_price = cart.get_total_cart_price()
    
    # Retrieve the receive_method from the session
    receive_method = request.session.get('receive_method', 'Pickup')
    shipping_fee = Decimal('0.00')
    
    # Calculate shipping fee based on the receive_method and the customer's state
    if receive_method == 'Delivery':
        if customer.customer_state in ['Sabah', 'Sarawak']:
            shipping_fee = Decimal('12.00')
        else:
            shipping_fee = Decimal('7.00')
    
    # The total cost includes the shipping fee if applicable
    total_cost = plant_price + shipping_fee

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        # Create a Payment instance using your model's fields
        payment = Payment.objects.create(
            customer=customer,
            shipping_fee=shipping_fee,
            payment_cost=total_cost,  # Total cost including shipping
            receive_method=receive_method,
            order_date=timezone.now().date(),  # Sets the order date to current date
            order_total_price=plant_price,  # Assuming this is the cost without shipping
        )
        
        # Create an Order instance and link the Payment instance
        with transaction.atomic():
            for item in items:
                plant = item.plant
                if plant.plant_availability >= item.cart_plant_quantity:
                    plant.plant_availability -= item.cart_plant_quantity
                    plant.save()
                else:
                    # Handle the case where there isn't enough stock
                    messages.error(request, f'Not enough {plant.plant_name} in stock.')
                    return redirect('view_cart')
                
        with transaction.atomic():
            new_order = Order.objects.create(
                customer=customer, 
                payment=payment,
                order_status='Waiting'  # Or any other status you wish to start with
            )
            for item in items:
                OrderItem.objects.create(
                    order=new_order,
                    plant=item.plant,
                    plant_quantity=item.cart_plant_quantity,
                    order_item_price=item.plant.plant_price,
                )   
             
            cart.delete()  # Clear the shopping cart

        messages.success(request, 'Your payment has been successfully processed. Your order ID is {}'.format(new_order.id))
        return redirect('plant_list')

    # Include the necessary data in the context for rendering
    context = {
        'total_cost': total_cost,
        'plant_price': plant_price,
        'shipping_fee': shipping_fee,
        'receive_method': receive_method.title()  # Assuming you want to display "Pickup" or "Delivery" in the template
    }
    return render(request, 'make_payment.html', context)

@login_required
def my_orders(request):
    customer = request.user.customer_profile
    orders = Order.objects.filter(customer=customer).prefetch_related('order_items', 'payment')
    context = {'orders': orders}
    return render(request, 'my_orders.html', context)

@login_required
def account_settings(request):
    customer = request.user.customer_profile
    context = {
        'customer': customer
    }
    return render(request, 'account_settings.html', context)

@login_required
def update_profile(request):
    customer = request.user.customer_profile
    valid_states = ['Johor', 'Kedah', 'Kelantan', 'Malacca', 'Negeri Sembilan', 'Pahang', 'Penang', 'Perak', 'Perlis', 'Sabah', 'Sarawak', 'Selangor', 'Terengganu', 'Kuala Lumpur', 'Labuan', 'Putrajaya']
    if request.method == 'POST':
        errors = False  # Flag to track if any validation errors occur

        # Full Name validation
        full_name = request.POST.get('full_name', '').strip()
        if not (10 <= len(full_name) <= 50):
            messages.error(request, 'Full name must be between 10 and 50 characters long.')
            errors = True
        
        # Email validation
        email = request.POST.get('email', '').strip()
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Enter a valid email address.')
            errors = True
        
        # Phone Number validation
        phone_number = request.POST.get('phone_number', '').strip()
        phone_regex = RegexValidator(regex=r'^60\d{9,10}$', message="Phone number must be entered in the format: '60123456789'. Up to 11 digits allowed.")
        try:
            phone_regex(phone_number)
        except ValidationError:
            messages.error(request, 'Invalid phone number format. Ensure it starts with 60 and is followed by 9 or 10 digits.')
            errors = True
        
        # Address validation
        address = request.POST.get('address', '').strip()
        if len(address) > 200:
            messages.error(request, 'Address must be under 200 characters long.')
            errors = True

        state = request.POST.get('state', '').strip().capitalize()
        valid_states_capitalized = [s.capitalize() for s in valid_states]  # Capitalize valid states for case-insensitive comparison
        if state not in valid_states_capitalized:
            messages.error(request, 'Invalid state. Please enter a valid state.')
            errors = True

        # IC Number validation
        ic_no = request.POST.get('ic_no', '').strip()
        if not (len(ic_no) == 12 and ic_no.isdigit()):
            messages.error(request, 'IC Number must consist of 12 digits.')
            errors = True

        if errors:
            # If there were errors, re-render the page with the form data and errors
            return render(request, 'edit_profile.html', {
                'customer': customer,
                'full_name': request.POST.get('full_name', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'phone_number': request.POST.get('phone_number', '').strip(),
                'address': request.POST.get('address', '').strip(),
                'state': state,
                'ic_no': request.POST.get('ic_no', '').strip(),
            })
        else:
            # No errors, update the customer profile
            customer.customer_name = request.POST.get('full_name', '').strip()
            customer.user.email = request.POST.get('email', '').strip()
            customer.customer_phone_number = request.POST.get('phone_number', '').strip()
            customer.customer_address = request.POST.get('address', '').strip()
            customer.customer_state = state
            customer.customer_ic = request.POST.get('ic_no', '').strip()
            customer.save()
            customer.user.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('account_settings')
    else:
        # GET request, render the page with the customer's current data
        return render(request, 'edit_profile.html', {'customer': customer})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('account_settings')  # Redirect to the account settings page
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})
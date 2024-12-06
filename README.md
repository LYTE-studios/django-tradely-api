
# Django Tradely API (DJANGO-TRADELY-API)

We are developing a trade journaling platform that integrates with MetaTrader and TradeLocker APIs to fetch and display trade data. Users can also save notes per date.

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/LYTE-studios/https://github.com/LYTE-studios/django-tradely-api.git
   cd django-jobr-api
   ```


2. Apply migrations:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Create a superuser (optional, for accessing admin features):

   ```bash
   python manage.py createsuperuser
   ```

4. Run the server:

   ```bash
   python manage.py runserver
   ```

## API Endpoints

### 1. User Registration

- **POST** `/api/accounts/register/`
  
**Request Body:**

```json
{
    "username": "newuser",
    "email": "new@example.com",
    "password": "newpassword"
}
```

**Response:**

- **201 Created** on successful registration, returning the user details.

![Register API](https://awesomescreenshot.s3.amazonaws.com/image/2631307/51764602-f86ecdbe2f913812bc5b4e92a075727a.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAJSCJQ2NM3XLFPVKA%2F20241126%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20241126T185608Z&X-Amz-Expires=28800&X-Amz-SignedHeaders=host&X-Amz-Signature=a93ace125ccba11312b7f0f4025fc221852c2de957471b37deb43a2f93b74993)
### 2. User Login

- **POST** `/api/accounts/login/`
  
**Request Body:**

```json
{
    "username": "testuser",
    "password": "securepassword"
}
```
**Response:**

- **200 OK** on successful login with a message.
![Login API](https://awesomescreenshot.s3.amazonaws.com/image/2631307/51764682-ae8fecb59cc85cbc980be220c40f3dd9.png?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAJSCJQ2NM3XLFPVKA%2F20241126%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20241126T185950Z&X-Amz-Expires=28800&X-Amz-SignedHeaders=host&X-Amz-Signature=4fb1ad0b6943f34e44faa45077f5aae0da4455622cd2d938af8f103547454cd0)

  
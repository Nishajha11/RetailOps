from tkinter import *
from PIL import Image, ImageTk
from customer import customerClass
from category import categoryClass
from productex import productClass
from sales import salesClass
from billing import BillClass
import sqlite3
from tkinter import messagebox
import os
import time
from tkinter import Tk,Label,Frame
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from statsmodels.tsa.statespace.sarimax import SARIMAX

import pandas as pd
from matplotlib.figure import Figure
from sklearn.neighbors import NearestNeighbors

class IMS:
    def __init__(self,root):
       self.root=root
       self.root.geometry("1350x700+0+0")
       self.root.title("Inventory Management System | Develop by NDV")
       self.root.config(bg="white")
       #title
       self.icon_title = PhotoImage(file="images/logo1.png")
       title=Label(self.root,text="RetailsOps",image=self.icon_title,compound=LEFT,font=("times new roman",40,"bold"),bg="#010c48",fg="white",anchor="w",padx=20).place(x=0,y=0,relwidth=1,height=70)
       
       #user
       #self.lbl_username = Label(self.root, text="Username:", font=("times new roman", 16), bg="white")
       #self.lbl_username.place(x=400, y=20)
       #self.ent_username = Entry(self.root, font=("times new roman", 16), bg="lightgray")
       #self.ent_username.place(x=510, y=20)
       
       #self.lbl_password = Label(self.root, text="Password:", font=("times new roman", 16), bg="white")
       #self.lbl_password.place(x=400, y=60)
       #self.ent_password = Entry(self.root, font=("times new roman", 16), bg="lightgray", show="*")
       #self.ent_password.place(x=510, y=60)
       
       #self.btn_login = Button(self.root, text="Login", font=("times new roman", 16, "bold"), bg="green", fg="white", command=self.login)
       #self.btn_login.place(x=510, y=100)
       
       #button logout
       btn_logout=Button(self.root,text="Logout",command=self.logout,font=("times new roman",15,"bold"),bg="yellow",cursor="hand2").place(x=1100,y=10,height=50,width=150)

       #clock
       self.lbl_clock=Label(self.root,text="Welcome to Our Website\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS",font=("times new roman",15),bg="#4d636d",fg="white")
       self.lbl_clock.place(x=0,y=70,relwidth=1,height=30)
       
       #left menu
       self.MenuLogo=Image.open("images/nsk.jpeg")
       self.MenuLogo=self.MenuLogo.resize((200,200),Image.LANCZOS)
       self.MenuLogo=ImageTk.PhotoImage(self.MenuLogo)
       LeftMenu=Frame(self.root,bd=2,relief=RIDGE,bg="white")
       LeftMenu.place(x=0,y=102,width=200,height=537)

       lbl_menuLogo=Label(LeftMenu,image=self.MenuLogo)
       lbl_menuLogo.pack(side=TOP,fill=X)
       
       self.icon_side = PhotoImage(file="images/side.png")
       lbl_menu=Label(LeftMenu,text="Menu",font=("times new roman",24),bg="#010c48",fg="white").pack(side=TOP,fill=X)
      
    #customer button
       image = Image.open("images/customer.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_customer = ImageTk.PhotoImage(resized_image)
       btn_customer = Button(LeftMenu, text="Customer",command=self.customer, image=self.icon_customer, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_customer.pack(side=TOP, fill=X, pady=0)
       
    #product button
       image = Image.open("images/product.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_product= ImageTk.PhotoImage(resized_image)
       btn_product = Button(LeftMenu, text="Product",command=self.productex, image=self.icon_product, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_product.pack(side=TOP, fill=X, pady=0)
    
    
    #sales button
       image = Image.open("images/s.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_s= ImageTk.PhotoImage(resized_image)
       btn_sales = Button(LeftMenu, text="Sales", command=self.sales, image=self.icon_s, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_sales.pack(side=TOP, fill=X, pady=0)
       
    #order button
       image = Image.open("images/order.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_order= ImageTk.PhotoImage(resized_image)
       btn_order = Button(LeftMenu, text="Order", image=self.icon_order, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_order.pack(side=TOP, fill=X, pady=0)
       
    #category button
       image = Image.open("images/c.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_c= ImageTk.PhotoImage(resized_image)
       btn_category = Button(LeftMenu, text="Category", command=self.category, image=self.icon_c, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_category.pack(side=TOP, fill=X, pady=0)
       
    #bills button 
       image = Image.open("images/bills.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_bills= ImageTk.PhotoImage(resized_image)
       btn_bills = Button(LeftMenu, text="Bills", command=self.bills, image=self.icon_bills, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_bills.pack(side=TOP, fill=X, pady=0)
       
    #exit button   
       image = Image.open("images/exit.png")
       resized_image = image.resize((20, 20), Image.LANCZOS)  # Adjust dimensions as needed
       self.icon_exit= ImageTk.PhotoImage(resized_image)
       btn_exit = Button(LeftMenu, text="Exit", image=self.icon_exit, compound=LEFT, padx=16, anchor="w",
                             font=("times new roman", 15, "bold"), bg="white", fg="black", bd=3, cursor="hand2")
       btn_exit.pack(side=TOP, fill=X, pady=0)
       
      #content
        # Customer Outer frame
       customer_frame = Frame(self.root, bd=5, relief=RIDGE)
       customer_frame.place(x=220, y=120, width=200, height=120)

        # Colored background with image (left side)
       image_frame = Frame(customer_frame, bg="#010c48")
       image_frame.pack(side=LEFT, fill=BOTH, expand=True)
       image = Image.open("images/cusbox.png")  # Image path needs to be adjusted
       resized_image = image.resize((70, 70), Image.LANCZOS)
       self.icon_customer_image = ImageTk.PhotoImage(resized_image)
       lbl_customer_image = Label(image_frame, image=self.icon_customer_image, bg="#010c48")
       lbl_customer_image.pack(expand=True, padx=10, pady=5)

        # White background with text (right side)
       text_frame = Frame(customer_frame, bg="white")
       text_frame.pack(side=RIGHT, fill=BOTH, expand=True)
       lbl_customer_text = Label(text_frame, text="Customer\n[0]", font=("goudy old style", 14, "bold"), bg="white", fg="black")
       lbl_customer_text.pack(expand=True, padx=10, pady=5)

        # Product Outer frame
       product_frame = Frame(self.root, bd=5, relief=RIDGE)
       product_frame.place(x=430, y=120, width=200, height=120)

        # Colored background with image (left side) - Product
       image_frame_prod = Frame(product_frame, bg="#010c48")
       image_frame_prod.pack(side=LEFT, fill=BOTH, expand=True)
       image_prod = Image.open("images/probox.png")  # Image path needs to be adjusted
       resized_image_prod = image_prod.resize((70, 70), Image.LANCZOS)
       self.icon_product_image = ImageTk.PhotoImage(resized_image_prod)
       lbl_product_image = Label(image_frame_prod, image=self.icon_product_image, bg="#010c48")
       lbl_product_image.pack(expand=True, padx=10, pady=5)

        # White background with text (right side) - Product
       text_frame_prod = Frame(product_frame, bg="white")
       text_frame_prod.pack(side=RIGHT, fill=BOTH, expand=True)
       lbl_product_text = Label(text_frame_prod, text="Product\n[0]",font=("goudy old style", 15, "bold"), bg="white", fg="black")
       lbl_product_text.pack(expand=True, padx=10, pady=5)

        # Sales Outer frame
        # Sales Frame
       sales_frame = Frame(self.root, bd=5, relief=RIDGE)
       sales_frame.place(x=640, y=120, width=200, height=120)

        # Colored background with image (left side) - Sales
       image_frame_sales = Frame(sales_frame, bg="#010c48")
       image_frame_sales.pack(side=LEFT, fill=BOTH, expand=True)
       image_sales = Image.open("images/salbox.png")  # Image path needs to be adjusted
       resized_image_sales = image_sales.resize((70, 70), Image.LANCZOS)
       self.icon_sales_image = ImageTk.PhotoImage(resized_image_sales)
       lbl_sales_image = Label(image_frame_sales, image=self.icon_sales_image, bg="#010c48")
       lbl_sales_image.pack(expand=True, padx=10, pady=5)

        # White background with text (right side) - Sales
       text_frame_sales = Frame(sales_frame, bg="white")
       text_frame_sales.pack(side=RIGHT, fill=BOTH, expand=True)
       lbl_sales_text = Label(text_frame_sales, text="Sales\n[0]", font=("goudy old style", 15, "bold"), bg="white", fg="black")
       lbl_sales_text.pack(expand=True, padx=10, pady=5)

        # Order Outer frame
       order_frame = Frame(self.root, bd=5, relief=RIDGE)
       order_frame.place(x=850, y=120, width=200, height=120)

        # Colored background with image (left side) - Order
       image_frame_order = Frame(order_frame, bg="#010c48")
       image_frame_order.pack(side=LEFT, fill=BOTH, expand=True)
       image_order = Image.open("images/ordbox.png")  # Image path needs to be adjusted
       resized_image_order = image_order.resize((70, 70), Image.LANCZOS)
       self.icon_order_image = ImageTk.PhotoImage(resized_image_order)
       lbl_order_image = Label(image_frame_order, image=self.icon_order_image, bg="#010c48")
       lbl_order_image.pack(expand=True, padx=10, pady=5)

        # White background with text (right side) - Order
       text_frame_order = Frame(order_frame, bg="white")
       text_frame_order.pack(side=RIGHT, fill=BOTH, expand=True)
       lbl_order_text = Label(text_frame_order, text="Order\n[0]", font=("goudy old style", 14, "bold"), bg="white", fg="black")
       lbl_order_text.pack(expand=True, padx=10, pady=5)

        # Category Outer frame
       category_frame = Frame(self.root, bd=5, relief=RIDGE)
       category_frame.place(x=1060, y=120, width=200, height=120)

        # Colored background with image (left side) - Category
       image_frame_category = Frame(category_frame, bg="#010c48")
       image_frame_category.pack(side=LEFT, fill=BOTH, expand=True)
       image_category = Image.open("images/casbox.png")  # Image path needs to be adjusted
       resized_image_category = image_category.resize((70, 70), Image.LANCZOS)
       self.icon_category_image = ImageTk.PhotoImage(resized_image_category)
       lbl_category_image = Label(image_frame_category, image=self.icon_category_image, bg="#010c48")
       lbl_category_image.pack(expand=True, padx=10, pady=5)

        # White background with text (right side) - Category
       text_frame_category = Frame(category_frame, bg="white")
       text_frame_category.pack(side=RIGHT, fill=BOTH, expand=True)
       lbl_category_text = Label(text_frame_category, text="Category\n[0]", font=("goudy old style", 14, "bold"), bg="white", fg="black")
       lbl_category_text.pack(expand=True, padx=10, pady=5)

#footer 
       lbl_footer = Label(self.root, text="Inventory Management System | Developed by NDV | For any Technical Issue Contact: 9876543210  |  Email Id: nsk3@gmail.com", font=("times new roman", 13), bg="#4d636d", fg="white", justify='center')
       lbl_footer.pack(side=BOTTOM, fill='x', padx=0, pady=14)



# Call method to create table 
       self.create_table()
       self.create_another_table()

    def get_recommended_products(self):
        sales_data = pd.read_excel('NSK_Dataset.xlsx', sheet_name='Sales', parse_dates=['Date'])
        product_data = pd.read_excel('product.xlsx')

        merged_data = pd.merge(sales_data, product_data[['product_id', 'product_name']], on='product_id', how='left')

        product_sales = merged_data.groupby('product_id')['order_qty'].sum().reset_index()

        knn_model = NearestNeighbors(n_neighbors=6)  # We set k=6 to include the product itself
        knn_model.fit(product_sales[['order_qty']])

        query_product = [[product_sales['order_qty'].max()]]  # Use the highest sales as a reference
        distances, indices = knn_model.kneighbors(query_product)

        recommended_products = product_sales.iloc[indices[0][1:]]  # Exclude the product itself
        recommended_products = pd.merge(recommended_products, product_data, on='product_id', how='left')
        recommended_products = recommended_products.sort_values(by='order_qty', ascending=False).head(5)
        return recommended_products

#create first table
    def create_table(self):
        # Calculate the height of the table up to the footer
        table_height = self.root.winfo_screenheight() - 250  # Adjust the value as needed

        # Table "Highest Selling Product"
        table_frame = Frame(self.root, bd=5, relief=RIDGE)
        table_frame.place(x=220, y=250, width=350, height=400)

        # Load and resize the image with LANCZOS
        image = Image.open("images/dicebox.png")
        image = image.resize((30, 30), Image.LANCZOS)
        img = ImageTk.PhotoImage(image)

        # Label to display the image
        lbl_image = Label(table_frame, image=img)
        lbl_image.image = img  # Keep a reference to avoid garbage collection
        lbl_image.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Table title with image
        lbl_table_title = Label(table_frame, text="Top 5 Recommended Products", font=("goudy old style", 16, "bold"), fg="black")
        lbl_table_title.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Navy blue line separator
        line_frame = Frame(table_frame, bg="#010c48", height=2)
        line_frame.grid(row=1, column=0, columnspan=3, sticky="ew")

        # Display the recommended products
        recommended_products = self.get_recommended_products()  # Call the method using self
        for i, (product_id, product_name, order_qty) in enumerate(recommended_products[['product_id', 'product_name', 'order_qty']].values):
            lbl_product = Label(table_frame, text=f"{i+1}. {product_name} - {order_qty}", font=("goudy old style", 12), bg="white", fg="black")
            lbl_product.grid(row=i+2, column=0, padx=10, sticky="w")
        # Adjust row and column configurations for better layout
        table_frame.grid_rowconfigure((1, 4), weight=0)
        table_frame.grid_columnconfigure(0, weight=1)


    
    def create_another_table(self):
    # Calculate the height of the table up to the footer
        table_height = self.root.winfo_screenheight() - 250  # Adjust the value as needed

        # Table "Highest Selling Product"
        another_table_frame = Frame(self.root, bd=5, relief=RIDGE)
        another_table_frame.place(x=720, y=250, width=490, height=400)

    # Load and resize the image with LANCZOS
        image = Image.open("images/dicebox.png")
        image = image.resize((30, 30), Image.LANCZOS)
        img = ImageTk.PhotoImage(image)

# Label to display the image
        lbl_image = Label(another_table_frame, image=img)
        lbl_image.image = img  # Keep a reference to avoid garbage collection
        lbl_image.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Table title with image
        lbl_another_table_title = Label(another_table_frame, text="Latest Sales", font=("goudy old style", 16, "bold"), fg="black")
        lbl_another_table_title.grid(row=0, column=0, columnspan=3, padx=110, pady=5, sticky="ew")

#blue line separator
        line_frame = Frame(another_table_frame, bg="#010c48", height=2)
        line_frame.grid(row=1, column=0, columnspan=3, sticky="ew")

    def create_another_table(self):
        # Calculate the height of the table up to the footer
        table_height = self.root.winfo_screenheight() - 250  # Adjust the value as needed

        # Table "Latest Sales"
        another_table_frame = Frame(self.root, bd=5, relief=RIDGE)
        another_table_frame.place(x=580, y=250, width=680, height=400)

        # Load and display the sales forecast plot using the new function
        fig = plot_sales_forecast()  # Call the new function

        # Embed the figure in a Tkinter canvas
        canvas = FigureCanvasTkAgg(fig, master=another_table_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

#sales window  
    def productex(self):
      self.new_win=Toplevel(self.root)
      self.new_obj=productClass(self.new_win)

#customer
    def customer(self):
      self.new_win=Toplevel(self.root)
      self.new_obj=customerClass(self.new_win)


    def category(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)

    def sales(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)

    def bills(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = BillClass(self.new_win)

    def update_content(self):
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from product")
            product = cur.fetchall()
            self.lbl_product.config(text=f'Total Products\n[{str(len(product))}]')

            cur.execute("select * from customer")
            customer = cur.fetchall()
            self.lbl_customer.config(text=f'Total Suppliers\n[{str(len(customer))}]')

            cur.execute("select * from category")
            category = cur.fetchall()
            self.lbl_categories.config(text=f'Total Categories\n[{str(len(category))}]')


            time_ = time.strftime("%I:%M:%S")
            date_ = time.strftime("%d-%m-%Y")
            self.lbl_clock.config(
            text=f"Welcome to Inventory Management System\t\t Date: {str(date_)}\t\t Time: {str(time_)}")
            self.lbl_clock.after(200, self.update_content)
        except Exception as ex:
               messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def logout(self):
        self.root.destroy()
        os.system("python loginpage.py")

def plot_sales_forecast():
    # Generate forecasted sales plot
    sales_data = pd.read_excel('NSK_Dataset.xlsx', sheet_name='Sales', parse_dates=['Date'])
    product_data = pd.read_excel('product.xlsx')

    sales_data = pd.merge(sales_data, product_data[['product_id', 'rate']], on='product_id', how='left')

    monthly_sales = sales_data.resample('M', on='Date').sum()

    monthly_sales['total_sales_amount'] = monthly_sales['order_qty'] * monthly_sales['rate']

    model = SARIMAX(monthly_sales['total_sales_amount'], order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
    result = model.fit()

    # Forecast the sales for the next month
    next_month_forecast = result.forecast(steps=5)

    # Create the plot
    fig = Figure(figsize=(4, 4))
    ax = fig.add_subplot(111)
    ax.plot(monthly_sales.index, monthly_sales['total_sales_amount'], marker='o', label='Historical Sales')
    ax.plot(next_month_forecast.index, next_month_forecast.values, marker='o', label='Forecasted Sales')
    ax.set_title('Monthly Sales Forecast')
    ax.set_xlabel('Date')
    ax.set_ylabel('Total Sales Amount')
    ax.legend()
    ax.grid(True)

    return fig

if __name__ == "__main__":
    root = Tk()
    obj = IMS(root)
    root.mainloop()

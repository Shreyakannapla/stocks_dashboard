import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

# ---------------- BUY / SELL PAGE ----------------
def show_buy_sell_stock_page():
    st.title("Buy/Sell Stocks and F&O")

    ticker = st.text_input("Enter Stock Ticker", "AAPL")
    quantity = st.number_input("Quantity to Buy", min_value=1, value=1)

    try:
        stock_data = yf.Ticker(ticker).history(period="1d", interval="1m")

        if stock_data.empty:
            st.warning(f"No data for ticker: {ticker}. Check symbol.")
        else:
            latest_price = stock_data['Close'].iloc[-1]
            st.subheader(f"Latest Price: ${latest_price:.2f}")

            user_profile = st.session_state.get('user_profile', None)
            if user_profile:
                bank_balance = user_profile['bank_balance']
                st.write(f"*Current Bank Balance:* ${bank_balance:.2f}")

            # BUY STOCK
            if st.button("Buy Stock"):
                total_cost = latest_price * quantity
                if total_cost <= bank_balance:
                    user_profile['bank_balance'] -= total_cost
                    user_profile['stocks'][ticker] = user_profile['stocks'].get(ticker, 0) + quantity
                    user_profile['transactions'].append({
                        "action": "Buy",
                        "ticker": ticker,
                        "quantity": quantity,
                        "price": latest_price,
                        "total_cost": total_cost,
                        "balance": user_profile['bank_balance']
                    })
                    st.session_state.user_profile = user_profile
                    st.success(f"Bought {quantity} shares of {ticker} at ${latest_price:.2f}")
                else:
                    st.warning("Insufficient funds.")

            # SELL STOCK (if owned)
            if ticker in user_profile['stocks'] and user_profile['stocks'][ticker] > 0:
                max_qty = user_profile['stocks'][ticker]
                sell_quantity = st.number_input(f"Quantity to Sell (max {max_qty})", min_value=1, max_value=max_qty, value=1)

                if st.button("Sell Stock"):
                    total_value = latest_price * sell_quantity
                    user_profile['bank_balance'] += total_value
                    user_profile['stocks'][ticker] -= sell_quantity
                    if user_profile['stocks'][ticker] == 0:
                        del user_profile['stocks'][ticker]
                    user_profile['transactions'].append({
                        "action": "Sell",
                        "ticker": ticker,
                        "quantity": sell_quantity,
                        "price": latest_price,
                        "total_value": total_value,
                        "balance": user_profile['bank_balance']
                    })
                    st.session_state.user_profile = user_profile
                    st.success(f"Sold {sell_quantity} shares of {ticker} at ${latest_price:.2f}")

            fig = go.Figure(data=[go.Candlestick(
                x=stock_data.index,
                open=stock_data['Open'],
                high=stock_data['High'],
                low=stock_data['Low'],
                close=stock_data['Close']
            )])
            st.plotly_chart(fig)

    except Exception as e:
        st.error(f"Error fetching stock data: {e}")

# ---------------- DATA FETCHING ----------------
def get_stock_data(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d", interval="1m")
        if data.empty:
            return None
        data['Date'] = pd.to_datetime(data.index)
        return data
    except:
        return None

def get_futures_data(ticker):
    return get_stock_data(ticker)

def get_options_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        options = stock.options
        if not options:
            return None
        option_data = {}
        for expiry in options:
            opt_chain = stock.option_chain(expiry)
            option_data[expiry] = {
                "calls": opt_chain.calls,
                "puts": opt_chain.puts
            }
        return option_data
    except:
        return None

# ---------------- DISPLAY ----------------
def display_data(ticker, chart_type, data_type):
    if data_type == "Stock Data":
        data = get_stock_data(ticker)
    elif data_type == "Futures Data":
        data = get_futures_data(ticker)
    else:
        data = None

    if data is None or data.empty:
        st.warning(f"No {data_type} for {ticker}")
        return
    
    st.dataframe(data[['Date', 'Open', 'High', 'Low', 'Close']])

    if chart_type == "Line":
        st.line_chart(data['Close'])
    elif chart_type == "Candlestick":
        fig = go.Figure(data=[go.Candlestick(x=data['Date'],
                                             open=data['Open'],
                                             high=data['High'],
                                             low=data['Low'],
                                             close=data['Close'])])
        st.plotly_chart(fig)
    elif chart_type == "Bar Chart":
        st.bar_chart(data['Close'])

def display_options_data(ticker):
    option_data = get_options_data(ticker)
    if option_data is None:
        st.warning("No options data.")
        return

    selected_expiry = st.selectbox("Select Expiry", list(option_data.keys()))
    if selected_expiry:
        st.write("Calls:")
        st.dataframe(option_data[selected_expiry]["calls"])
        st.write("Puts:")
        st.dataframe(option_data[selected_expiry]["puts"])

# ---------------- DASHBOARD ----------------
def dashboard():
    if 'user_email' not in st.session_state:
        st.error("Please log in again.")
        return

    st.title("Stocks F&O Dashboard")

    ticker = st.sidebar.text_input("Enter Stock Ticker", "AAPL")
    chart_type = st.sidebar.selectbox("Chart Type", ["Candlestick", "Line", "Bar Chart"])
    data_type = st.sidebar.selectbox("Data Type", ["Stock Data", "Futures Data", "Options Data"])

    if data_type == "Options Data":
        display_options_data(ticker)
    else:
        display_data(ticker, chart_type, data_type)

# ---------------- PROFILE ----------------
def display_profile():
    user_profile = st.session_state.get('user_profile', None)
    if user_profile:
        st.write(f"*Name:* {user_profile['name']}")
        st.write(f"*Email:* {user_profile['email']}")
        st.write(f"*Bank Balance:* ${user_profile['bank_balance']:.2f}")

        if user_profile['stocks']:
            st.subheader("Owned Stocks")
            for stock, qty in user_profile['stocks'].items():
                st.write(f"{stock}: {qty} shares")

        st.subheader("Transactions")
        if user_profile['transactions']:
            st.dataframe(pd.DataFrame(user_profile['transactions']))
        else:
            st.info("No transactions yet.")

        # Add Funds
        st.subheader("Add Funds")
        add_amount = st.number_input("Amount to Add", min_value=1, value=100, key="add_amount_input")
        if st.button("Add Money"):
            st.session_state.user_profile['bank_balance'] += add_amount
            st.success(f"Added ${add_amount:.2f} to your bank balance.")
            st.rerun()
    else:
        st.error("Profile not found.")

# ---------------- AUTH ----------------
def show_login_page():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if email and password:
            st.session_state.logged_in = True
            st.session_state.user_email = email
            if 'user_profile' not in st.session_state:
                st.session_state.user_profile = {
                    "name": email.split("@")[0],  # fallback only if not signed up
                    "email": email,
                    "bank_balance": 1000.00,
                    "transactions": [],
                    "stocks": {}
                }
            st.rerun()
        else:
            st.error("Enter both email & password.")

def show_signup_page():
    st.title("Sign Up")
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        if name and email and password:
            st.session_state.logged_in = True
            st.session_state.user_email = email
            st.session_state.user_profile = {
                "name": name,
                "email": email,
                "bank_balance": 1000.00,
                "transactions": [],
                "stocks": {}
            }
            st.rerun()
        else:
            st.error("Fill all fields.")

# ---------------- MAIN ----------------
def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        page = st.sidebar.radio("Navigate", ["Dashboard", "Buy/Sell Stock", "Profile", "Logout"], index=0)

        if page == "Dashboard":
            dashboard()
        elif page == "Buy/Sell Stock":
            show_buy_sell_stock_page()
        elif page == "Profile":
            display_profile()
        elif page == "Logout":
            st.session_state.clear()
            st.success("Logged out!")
            st.rerun()
    else:
        page = st.sidebar.radio("Navigate", ["Login", "Sign Up"])
        if page == "Login":
            show_login_page()
        elif page == "Sign Up":
            show_signup_page()

if __name__ == "__main__":
    main()

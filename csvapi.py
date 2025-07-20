from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import re
from typing import Dict, Any
from datetime import datetime

app = FastAPI(title="CSV Analyzer", description="Analyzes CSV files for Food category spending")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_amount(amount_str):
    """Clean and convert amount string to float"""
    if pd.isna(amount_str) or amount_str == '':
        return 0.0
    
    # Convert to string and strip whitespace
    amount_str = str(amount_str).strip()
    
    # Remove currency symbols, commas, and extra spaces
    amount_str = re.sub(r'[$€£¥₹,\s]', '', amount_str)
    
    # Handle parentheses for negative numbers
    if amount_str.startswith('(') and amount_str.endswith(')'):
        amount_str = '-' + amount_str[1:-1]
    
    try:
        return float(amount_str)
    except (ValueError, TypeError):
        return 0.0

def clean_category(category_str):
    """Clean category string"""
    if pd.isna(category_str):
        return ''
    return str(category_str).strip().lower()

def clean_date(date_str):
    """Attempt to parse various date formats"""
    if pd.isna(date_str) or date_str == '':
        return None
    
    date_str = str(date_str).strip()
    
    # Common date formats to try
    date_formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
        '%Y/%m/%d', '%d.%m.%Y', '%m.%d.%Y', '%Y.%m.%d',
        '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y'
    ]
    
    for fmt in date_formats:
        try:
            return pd.to_datetime(date_str, format=fmt)
        except:
            continue
    
    # Try pandas auto-parsing as last resort
    try:
        return pd.to_datetime(date_str, infer_datetime_format=True)
    except:
        return None

@app.post("/analyze")
async def analyze_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Analyze CSV file and return total spending on Food category
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read the CSV file
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Clean column names - remove extra spaces and convert to lowercase
        df.columns = df.columns.str.strip().str.lower()
        
        # Identify potential column names for amount and category
        amount_cols = [col for col in df.columns if any(word in col for word in ['amount', 'cost', 'price', 'total', 'spend', 'expense'])]
        category_cols = [col for col in df.columns if any(word in col for word in ['category', 'type', 'class', 'group'])]
        date_cols = [col for col in df.columns if any(word in col for word in ['date', 'time', 'day'])]
        
        # Use the first matching column or make educated guesses
        amount_col = amount_cols[0] if amount_cols else (df.columns[1] if len(df.columns) > 1 else df.columns[0])
        category_col = category_cols[0] if category_cols else (df.columns[0] if len(df.columns) > 0 else None)
        
        if category_col is None:
            raise HTTPException(status_code=400, detail="Could not identify category column")
        
        # Clean the data
        df['clean_amount'] = df[amount_col].apply(clean_amount)
        df['clean_category'] = df[category_col].apply(clean_category)
        
        # If there's a date column, clean it too
        if date_cols:
            date_col = date_cols[0]
            df['clean_date'] = df[date_col].apply(clean_date)
        
        # Filter for food-related categories
        food_keywords = ['food', 'restaurant', 'grocery', 'dining', 'meal', 'lunch', 'dinner', 'breakfast', 'cafe', 'fast food', 'takeout']
        food_mask = df['clean_category'].str.contains('|'.join(food_keywords), na=False)
        
        # Calculate total food spending
        food_spending = df[food_mask]['clean_amount'].sum()
        
        return {
            "answer": round(food_spending, 2),
            "email": "analyst@example.com",  # Replace with your actual email
            "exam": "tds-2025-05-roe"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "CSV Analyzer API",
        "endpoint": "/analyze",
        "method": "POST",
        "description": "Upload CSV file to analyze Food category spending"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
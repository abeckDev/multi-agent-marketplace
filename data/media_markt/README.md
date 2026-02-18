# Media Markt Experimental Dataset

## Overview

This dataset represents a experimental marketplace for Media Markt, a major consumer electronics retailer in Germany. The dataset is designed to enable experiments on product recommendations, customer matching, and store location optimization within the multi-agent marketplace framework.

## Dataset Structure

The dataset follows the standard organizational pattern used in this repository:

```
media_markt/
├── businesses/          # Product offerings and store locations
│   ├── business_0001.yaml through business_0010.yaml  # Product listings
│   └── business_0011.yaml through business_0016.yaml  # Store locations
├── customers/           # Customer requests and preferences
│   └── customer_0001.yaml through customer_0010.yaml
├── baseline_utilities.json  # Baseline agent performance metrics (to be computed)
└── README.md           # This file
```

## Data Sources and Collection

### Product Data (business_0001 - business_0010)

Product data was collected based on representative examples from Media Markt's online storefront, capturing:

- **Electronics Categories**: TVs, Laptops, Tablets, Smartphones, Audio, Gaming, E-Mobility, Monitors
- **Major Brands**: Sony, Apple, LG, Samsung, Nintendo, Segway, MSI
- **Price Range**: €79 - €1,799 (representing budget to premium segments)

### Store Location Data (business_0011 - business_0016)

Store location data represents actual Media Markt stores in the Baden-Württemberg region of Germany:

- **Cities Covered**: Sinsheim, Heidelberg (3 locations including 1 Smart store), Bruchsal, Neckarsulm
- **Store Types**: 
  - Standard stores (5): Traditional Media Markt locations
  - Smart stores (1): Modern concept with enhanced digital experience and expert consultation

### Customer Data

Customer profiles were synthetically generated to represent diverse shopping scenarios and preferences typical of electronics retail customers.

## Data Schema

### Business Schema (Products)

Products (`business_0001` through `business_0010`) contain:

```yaml
id: integer                    # Unique identifier
name: string                   # Product name
description: string            # Full product description
rating: float                  # Customer rating (0-5 scale)
product_features:              # Product-specific attributes
  brand: string                # Manufacturer brand
  category: string             # Product category
  [category-specific fields]   # Varies by product type
  price: float                 # Current price in EUR
  original_price: float        # Original/list price in EUR
  discount_percent: integer    # Discount percentage
  energy_rating: string|null   # EU energy efficiency rating
amenity_features:              # Purchase/delivery options
  free_shipping: boolean       # Free delivery available
  cashback: boolean            # Cashback promotion available
  cashback_amount: float       # Cashback amount if applicable
  sponsored: boolean           # Sponsored/featured product
  tier_pricing: string|null    # Special pricing tier
  in_stock: boolean            # Product availability
  price_includes_vat: boolean  # VAT inclusion flag
progenitor_customer: integer   # Associated customer ID
min_price_factor: float        # Minimum price multiplier
```

### Business Schema (Stores)

Store locations (`business_0011` through `business_0016`) contain:

```yaml
id: integer                    # Unique identifier
name: string                   # Store name
description: string            # Store description
rating: float                  # Customer rating (0-5 scale)
store_features:                # Store-specific attributes
  type: string                 # "Standard" or "Smart"
  address: string              # Street address
  postal_code: string          # Postal code
  city: string                 # City name
  opening_hours: string        # Operating hours
  services: list[string]       # Available services
amenity_features:              # Store amenities
  parking: boolean             # Parking available
  wheelchair_accessible: boolean
  click_and_collect: boolean   # Click & collect service
  in_store_pickup: boolean     # In-store pickup available
  extended_hours: boolean      # Extended operating hours
  expert_consultation: boolean # Expert consultation (Smart stores)
  smart_store: boolean         # Smart store concept
  shopping_center: boolean     # Located in shopping center
progenitor_customer: null      # Not applicable for stores
min_price_factor: float        # Always 1.0 for stores
```

### Customer Schema

Customers contain:

```yaml
id: integer                    # Unique identifier
name: string                   # Customer name
request: string                # Natural language product request
product_features:              # Desired product attributes
  category: string             # Target category
  [feature-specific fields]    # Category-dependent requirements
  max_price: float             # Maximum budget in EUR
amenity_features:              # Required/preferred amenities
  - string                     # List of desired features
```

## Product Categories

The dataset includes the following product categories:

1. **TV & Sound**: Large-screen televisions with smart features
2. **Computers & Tablets**: Laptops, tablets, and computing devices
3. **Smartphones**: Mobile phones with various specifications
4. **Headphones**: Wireless audio devices
5. **Gaming**: Gaming consoles and bundles
6. **E-Mobility**: Electric scooters
7. **Monitors**: Computer displays for gaming and productivity

## Key Features for Experimentation

### Product Features

- **Price Optimization**: Wide price range with discounts (0-55% off)
- **Brand Diversity**: Multiple brands across categories
- **Rating Signals**: Product ratings range from 4.2 to 4.9
- **Energy Ratings**: EU energy labels (A through G) for applicable products
- **Promotions**: Various promotional types (cashback, free shipping, sponsored)

### Store Features

- **Geographic Distribution**: 6 stores across 5 cities in Baden-Württemberg
- **Store Differentiation**: Standard vs. Smart store concepts
- **Service Variety**: Different service offerings (pickup, consultation, technical support)
- **Accessibility**: Parking, wheelchair access, click & collect

### Customer Features

- **Diverse Budgets**: €150 to €2,500 maximum budgets
- **Category Coverage**: Requests span all product categories
- **Feature Preferences**: Specific requirements (brand, specifications, features)
- **Amenity Requirements**: Service and delivery preferences

## Potential Experiments

This dataset enables various experimental scenarios:

1. **Product Recommendation**: Match customer requests to optimal products based on features, price, and preferences
2. **Store Routing**: Recommend appropriate store locations based on customer location and store type
3. **Price Sensitivity Analysis**: Test agent behavior with different price ranges and discount levels
4. **Multi-objective Optimization**: Balance price, rating, features, and amenities
5. **Category-specific Matching**: Domain-specific matching logic for different product types
6. **Promotion Impact**: Analyze impact of cashback, free shipping, and other promotions
7. **Store Type Preference**: Compare standard vs. smart store recommendations

## Baseline Utilities

The `baseline_utilities.json` file is initialized with zero values. To compute actual baseline metrics:

1. Run the baseline computation script from the `data_generation_scripts` directory
2. Follow the pattern used for other datasets (mexican, contractors)
3. Update this file with computed baseline agent performance metrics

To compute baselines:

```bash
cd data/data_generation_scripts
# Adapt existing baseline computation script for media_markt dataset
# Example: ./compute_baselines.sh ../media_markt
```

## Data Quality Notes

### Assumptions

1. **Synthetic Customer Data**: Customer profiles are synthetically generated to represent realistic shopping scenarios
2. **Simplified Product Data**: Product specifications are simplified from actual Media Markt offerings
3. **Representative Sample**: 10 products represent the breadth of categories but not the full catalog depth
4. **Store Data Accuracy**: Store locations and types are based on public information as of February 2026
5. **Pricing**: Prices are representative examples and may not reflect current actual pricing

### Limitations

1. **Scale**: This is a small experimental dataset (10 products, 10 customers, 6 stores)
2. **Temporal**: Product availability and store information are point-in-time snapshots
3. **Completeness**: Not all product features are captured (e.g., detailed technical specs)
4. **Baseline Metrics**: Baseline utilities need to be computed post-generation

## Extensions and Future Work

Potential extensions to this dataset:

1. **Larger Scale**: Increase to 30, 99, or 300 products following the pattern of other datasets
2. **Seasonal Variations**: Create seasonal product availability patterns
3. **Dynamic Pricing**: Model price changes over time
4. **Inventory Levels**: Add stock quantity tracking
5. **Customer History**: Add purchase history to customer profiles
6. **Store Capacity**: Model store inventory and capacity constraints
7. **Delivery Options**: Expand delivery timeframes and methods
8. **Bundle Deals**: Add product bundle offerings

## Validation

To validate the dataset structure:

```bash
cd data/data_generation_scripts
python validate.py ../media_markt
```

This will check:
- YAML file syntax validity
- Required field presence
- Data type correctness
- Cross-reference integrity (customer/business IDs)

## Usage in Experiments

To use this dataset in marketplace experiments:

1. **Load Dataset**: Use the standard data loading utilities from the marketplace package
2. **Configure Experiment**: Set dataset path to `data/media_markt`
3. **Define Agents**: Configure customer and business agents with appropriate prompts
4. **Run Experiment**: Execute marketplace simulation with this dataset
5. **Analyze Results**: Compare agent performance against baseline utilities

Example configuration:

```yaml
experiment:
  name: "media_markt_matching"
  dataset: "data/media_markt"
  num_customers: 10
  num_businesses: 16
  ...
```

## Metadata

- **Dataset Name**: media_markt
- **Version**: 1.0
- **Created**: February 2026
- **Domain**: Consumer Electronics Retail
- **Geography**: Germany (Baden-Württemberg region)
- **Currency**: EUR (€)
- **Language**: Product names in German, field names in English

## Contact and Questions

For questions about this dataset or suggestions for improvements, please refer to the main repository documentation or open an issue in the GitHub repository.

## License

This dataset follows the license of the parent repository. Product names and brands are trademarks of their respective owners and are used here for experimental purposes only.

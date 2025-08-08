# Overview

SM2 Cloud is a comprehensive inventory management system built with Flask that provides a complete solution for managing products, customers, sales, purchases, and warehouses. The system includes a modern web interface with customizable color themes, point-of-sale (POS) functionality, multi-warehouse management, reporting capabilities, and user management with role-based access control.

The application serves businesses that need to track inventory across multiple warehouses, manage customer and supplier relationships, process sales and purchases, and generate various business reports. It includes features like barcode scanning, PDF invoice generation, email notifications, warehouse transfers, stock level monitoring, and comprehensive search and filtering capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI
- **JavaScript Framework**: jQuery with custom modules for POS, barcode scanning, and general functionality
- **CSS Framework**: Bootstrap 5 with custom theme system supporting multiple color schemes (blue, green, purple, orange)
- **UI Components**: DataTables for advanced table functionality, Font Awesome for icons
- **Real-time Features**: AJAX-based search, live cart updates in POS system, dynamic theme switching
- **Theme System**: Live theme switching with navbar controls and user profile customization

## Backend Architecture
- **Web Framework**: Flask with Blueprint-based modular architecture
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Authentication**: Session-based authentication with role-based access control (admin, manager, employee)
- **Caching**: Flask-Caching for performance optimization of frequent queries
- **File Structure**: Modular design with separate route blueprints for different functional areas

## Data Storage Solutions
- **Primary Database**: SQLite configured for local development with multi-threading support and PostgreSQL ready for production
- **Session Storage**: Filesystem-based session management
- **Caching Layer**: In-memory caching for dashboard statistics and frequent queries
- **File Storage**: Local filesystem for PDF generation and backup files
- **DIAN Integration**: Complete database schema for electronic invoicing compliance

## Key Data Models
- **User Management**: Users with role-based permissions and warehouse assignments
- **Inventory**: Products with categories, brands, groups, and multi-warehouse stock tracking
- **Transactions**: Sales and purchases with detailed line items and serial number tracking
- **Customer Management**: Unified customer/supplier/employee model with document management
- **Warehouse Management**: Multi-location inventory tracking with transfer capabilities

## Authentication and Authorization
- **Session Management**: Flask-Session with secure session handling
- **Password Security**: Werkzeug password hashing with salt
- **Access Control**: Decorator-based route protection with role verification
- **User Roles**: Three-tier permission system (admin, manager, employee)
- **Warehouse Restrictions**: Users can be assigned to specific warehouses

## Business Logic Features
- **Point of Sale**: Real-time product search, cart management, and invoice generation
- **Inventory Tracking**: Multi-warehouse stock levels with minimum stock alerts
- **Warehouse Management**: Complete warehouse administration, transfers between locations, stock level monitoring
- **Product Classification**: Categories, brands, and product grouping system
- **Barcode Support**: Scanner integration for product lookup and data entry
- **Document Generation**: PDF invoice creation with company branding
- **Reporting System**: Sales, purchase, and inventory reports with filtering
- **Serial Number Tracking**: Individual item tracking for warranty and service
- **Theme Customization**: User-selectable color schemes with live preview and persistence
- **Company Settings**: Comprehensive system configuration including branding and business rules
- **Accounting Module**: Complete double-entry bookkeeping system with chart of accounts
- **Journal Entries**: Full support for accounting transactions with automatic validation
- **Accounting Periods**: Time-based organization of financial data with period closure
- **Financial Reports**: Trial balance and other standard accounting reports
- **Colombian Localization**: Complete integration with all 1,118 Colombian cities and 33 departments
- **Currency Support**: Colombian peso (COP) formatting and calculations
- **Customer Data**: Separated first name and last name fields for proper Colombian naming conventions
- **DIAN Electronic Invoicing**: Full integration framework with authorized technology providers
- **Categories and Brands Management**: Complete CRUD operations for inventory classification
- **Multi-provider Support**: Framework supporting SIIGO, ALIADDO, CARVAJAL, and other DIAN providers

# External Dependencies

## Core Framework Dependencies
- **Flask**: Main web framework with extensions for SQLAlchemy, Mail, Caching, and Session management
- **SQLAlchemy**: Database ORM with PostgreSQL adapter
- **Werkzeug**: WSGI utilities and security functions
- **Jinja2**: Template engine (included with Flask)

## Frontend Dependencies
- **Bootstrap 5**: CSS framework delivered via CDN
- **jQuery**: JavaScript library for DOM manipulation and AJAX
- **Font Awesome**: Icon library via CDN
- **DataTables**: Advanced table functionality via CDN
- **ReportLab**: Python library for PDF generation

## Email and Communication
- **Flask-Mail**: Email sending capability configured for SMTP (Gmail by default)
- **SMTP Server**: External email service for invoice delivery and notifications

## Development and Deployment
- **ProxyFix**: Werkzeug middleware for handling proxy headers in production
- **Environment Variables**: Configuration via environment variables for security

## Database Configuration
- **SQLite**: Primary database for development with multi-threading support
- **PostgreSQL**: Available for production deployment with connection pooling
- **Colombian Localization**: Complete database with 1,118 cities covering all 33 departments of Colombia
- **Geographic Data**: All municipalities including Antioquia (125), Boyacá (122), Cundinamarca (116), Santander (87), Nariño (64), and all other departments
- **Accounting Tables**: Full chart of accounts and accounting periods for double-entry bookkeeping
- **DIAN Tables**: Complete schema for electronic invoicing, tax providers, and compliance
- **Connection Settings**: Optimized for concurrent access with automatic failover support

## Optional Integrations
- **Barcode Scanners**: Support for USB HID and camera-based barcode scanning
- **Backup System**: JSON-based data export/import functionality
- **Cache Backend**: Configurable caching system (filesystem by default, Redis-ready)

The system is designed to be deployment-ready with environment-based configuration and can scale from small businesses to larger operations with multiple warehouses and users.
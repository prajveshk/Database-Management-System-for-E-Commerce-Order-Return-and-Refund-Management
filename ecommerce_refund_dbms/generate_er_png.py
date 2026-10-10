import matplotlib.pyplot as plt
import matplotlib.patches as patches

def draw_er_diagram():
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Title
    ax.text(8, 9.5, "E-Commerce Order, Return & Refund DBMS - 3NF ER Diagram", 
            fontsize=16, fontweight='bold', ha='center', color='#2c3e50')

    entities = {
        'Role': (1, 8, ['role_id (PK)', 'role_name (UK)']),
        'AppUser': (4, 8, ['user_id (PK)', 'username (UK)', 'password_hash', 'role_id (FK)', 'customer_id (FK)']),
        'Customer': (8, 8, ['customer_id (PK)', 'name', 'email (UK)', 'phone', 'created_at']),
        'Product': (1, 5, ['product_id (PK)', 'name', 'current_price', 'return_window_days']),
        'Inventory': (1, 2, ['inventory_id (PK)', 'product_id (FK)', 'serial_or_sku (UK)', 'status']),
        'Orders': (8, 5, ['order_id (PK)', 'customer_id (FK)', 'order_date', 'total_amount', 'order_status']),
        'OrderItem': (4, 5, ['order_item_id (PK)', 'order_id (FK)', 'product_id (FK)', 'quantity', 'unit_price_at_purchase']),
        'Payment': (12, 8, ['payment_id (PK)', 'order_id (FK)', 'provider_reference (UK)', 'amount', 'payment_status']),
        'ReturnRequest': (8, 2, ['return_id (PK)', 'order_id (FK)', 'customer_id (FK)', 'reason', 'return_status']),
        'ReturnItem': (4, 2, ['return_item_id (PK)', 'return_id (FK)', 'order_item_id (FK)', 'quantity']),
        'Inspection': (12, 5, ['inspection_id (PK)', 'return_id (FK, 1:1)', 'inspector', 'condition_status', 'notes']),
        'Refund': (12, 2, ['refund_id (PK)', 'return_id (FK)', 'payment_id (FK)', 'amount', 'refund_status']),
        'AuditLog': (14, 0.5, ['log_id (PK)', 'entity_type', 'entity_id', 'old_status', 'new_status', 'actor', 'changed_at'])
    }

    colors = {
        'Role': '#e8f8f5', 'AppUser': '#e8f8f5', 'Customer': '#e8f8f5',
        'Product': '#fef9e7', 'Inventory': '#fef9e7',
        'Orders': '#ebf5fb', 'OrderItem': '#ebf5fb', 'Payment': '#ebf5fb',
        'ReturnRequest': '#fdf2e9', 'ReturnItem': '#fdf2e9', 'Inspection': '#fdf2e9', 'Refund': '#fdf2e9',
        'AuditLog': '#f4ecf7'
    }

    for name, (x, y, fields) in entities.items():
        w, h = 2.6, 0.4 + (len(fields) * 0.25)
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", 
                                     ec="#2c3e50", fc=colors[name], lw=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.2, name, fontsize=11, fontweight='bold', ha='center', color='#2c3e50')
        ax.plot([x, x + w], [y + h - 0.3, y + h - 0.3], color='#2c3e50', lw=1)
        for i, field in enumerate(fields):
            ax.text(x + 0.1, y + h - 0.5 - (i * 0.23), f"• {field}", fontsize=8, color='#34495e')

    # Draw relationship lines
    relationships = [
        ('Role', 'AppUser', '1:N'), ('Customer', 'AppUser', '1:1'),
        ('Customer', 'Orders', '1:N'), ('Product', 'Inventory', '1:N'),
        ('Product', 'OrderItem', '1:N'), ('Orders', 'OrderItem', '1:N'),
        ('Orders', 'Payment', '1:1'), ('Orders', 'ReturnRequest', '1:N'),
        ('OrderItem', 'ReturnItem', '1:N'), ('ReturnRequest', 'ReturnItem', '1:N'),
        ('ReturnRequest', 'Inspection', '1:1'), ('ReturnRequest', 'Refund', '1:N'),
        ('Payment', 'Refund', '1:N')
    ]

    plt.tight_layout()
    plt.savefig('docs/er_diagram.png', dpi=200, bbox_inches='tight')
    plt.close()
    print("ER Diagram PNG created at docs/er_diagram.png")

if __name__ == '__main__':
    draw_er_diagram()

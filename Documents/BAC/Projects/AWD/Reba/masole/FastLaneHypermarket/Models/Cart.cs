using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using FastLaneHypermarket.Models;
using Microsoft.EntityFrameworkCore;

namespace FastLaneHypermarket.Models
{
    public class CartItem
    {
        [Key]
        public int CartItemId { get; set; }

        [Required, ForeignKey("Customer")]
        public int CustomerId { get; set; }
        public Customer Customer { get; set; }

        [Required, ForeignKey("Product")]
        public int ProductId { get; set; }
        public Product Product { get; set; }

        [Required]
        [Range(1, int.MaxValue)]
        public int Quantity { get; set; }

        [NotMapped]
        public decimal Total => Product != null ? Quantity * Product.SellingPrice : 0;
    }
}


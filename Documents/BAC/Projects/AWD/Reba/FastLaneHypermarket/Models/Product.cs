using System.ComponentModel.DataAnnotations.Schema;
using System.ComponentModel.DataAnnotations;
using FastLaneHypermarket.Models;
using Microsoft.EntityFrameworkCore;

namespace FastLaneHypermarket.Models
{

    public class Product
    {
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        public int ProductCode { get; set; }

        public string ProductName { get; set; }
        public string Size { get; set; }
        public string Category { get; set; }
        public int Quantity { get; set; }
        public int ReorderLevel { get; set; }
        public decimal PurchasePrice { get; set; }
        public double PercentageMarkup { get; set; }

        public decimal SellingPrice { get; set; }
        public DateTime DatePurchased { get; set; }
        public string ProductStatus { get; set; }
        public string RecordedBy { get; set; }
        public string ImageUrl { get; set; }   // ✅ newly added column
    }
}


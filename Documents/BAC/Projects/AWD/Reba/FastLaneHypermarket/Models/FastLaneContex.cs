using System.Collections.Generic;
using Microsoft.EntityFrameworkCore;

namespace FastLaneHypermarket.Models
{
    public class FastLaneContext : DbContext
    {
        public FastLaneContext(DbContextOptions<FastLaneContext> options)
        : base(options) { }

        public DbSet<Product> Products { get; set; }
        public DbSet<Customer> Customers { get; set; }
        public DbSet<Staff> Staff { get; set; }
        public DbSet<Transaction> Transactions { get; set; }
    }
}

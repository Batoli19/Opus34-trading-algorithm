using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.Configuration;
using System.IO;

namespace FastLaneHypermarket.Models
{
    public class FastLaneContextFactory : IDesignTimeDbContextFactory<FastLaneContext>
    {
        public FastLaneContext CreateDbContext(string[] args)
        {
            // Build configuration from appsettings.json
            var configuration = new ConfigurationBuilder()
                .SetBasePath(Directory.GetCurrentDirectory())
                .AddJsonFile("appsettings.json")
                .Build();

            var optionsBuilder = new DbContextOptionsBuilder<FastLaneContext>();
            optionsBuilder.UseSqlServer(configuration.GetConnectionString("FastLaneDB"));

            return new FastLaneContext(optionsBuilder.Options);
        }
    }
}

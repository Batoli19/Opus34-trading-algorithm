using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace FastLaneHypermarket.Migrations
{
    /// <inheritdoc />
    public partial class RemoveTownFromStaff : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Town",
                table: "Staff",
                type: "nvarchar(max)",
                nullable: false,
                defaultValue: "");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "Town",
                table: "Staff");
        }
    }
}

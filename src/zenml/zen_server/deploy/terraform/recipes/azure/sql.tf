resource "azurerm_resource_group" "rg" {
  name     = var.resource_group
  location = var.location
}

resource "azurerm_mysql_flexible_server" "mysql" {
  name                   = var.db_instance_name
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  administrator_login    = var.database_username
  administrator_password = var.database_password == "" ? random_password.mysql_password.result : var.database_password
  version                = var.db_version
  storage {
    size_gb = var.db_disk_size
  }
  sku_name               = var.db_sku_name
}

resource "azurerm_mysql_flexible_database" "db" {
  name                = var.db_name
  resource_group_name = azurerm_resource_group.rg.name
  server_name         = azurerm_mysql_flexible_server.mysql.name
  charset             = "utf8"
  collation           = "utf8_unicode_ci"
}

resource "azurerm_mysql_flexible_server_firewall_rule" "allow_IPs" {
  name                = "all_traffic"
  resource_group_name = azurerm_resource_group.rg.name
  server_name         = azurerm_mysql_flexible_server.mysql.name
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "255.255.255.255"
}

resource "azurerm_mysql_flexible_server_configuration" "require_ssl" {
  name                = "require_secure_transport"
  resource_group_name = azurerm_resource_group.rg.name
  server_name         = azurerm_mysql_flexible_server.mysql.name
  value               = "OFF"
}

resource "random_password" "mysql_password" {
  length  = 12
  special = false
}

# download SSL certificate
resource "null_resource" "download-SSL-certificate" {
  provisioner "local-exec" {
    command = "wget https://dl.cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem"
  }

}
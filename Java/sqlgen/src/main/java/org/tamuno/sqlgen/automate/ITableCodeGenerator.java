/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.sqlgen.automate;

import java.sql.Connection;
import java.sql.SQLException;

/**
 *
 * @author kai
 */
public interface ITableCodeGenerator {

    public void appendCode(StringBuilder append, Connection connection, String catalog, String schema, String table) throws SQLException;
}

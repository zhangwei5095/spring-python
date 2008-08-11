"""
   Copyright 2006-2008 SpringSource (http://springsource.com), All Rights Reserved

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.       
"""
import warnings
warnings.warn("Expect three deprecation warnings: mysql, postgresql, and Sqlite have moved to the factory module.",
    stacklevel=2)

import logging
import os
import sys
import types
import unittest
from pmock import *
from springpython.context import XmlApplicationContext
from springpython.database import ArgumentMustBeNamed
from springpython.database import DataAccessException
from springpython.database import InvalidArgumentType
from springpython.database.core import DatabaseTemplate
from springpython.database import factory
from springpython.database import mysql
from springpython.database import postgresql
from springpython.database import Sqlite
from springpython.test.support import testSupportClasses

logger = logging.getLogger("springpython.test.databaseCoreTestCases")

class ConnectionFactoryTestCase(MockTestCase):
    """Testing the connection factories requires mocking the libraries they are meant to utilize."""

    def testConnectingToMySqlUsingDeprecatedConnectionFactory(self):
        sys.modules["MySQLdb"] = self.mock()
        sys.modules["MySQLdb"].expects(once()).method("connect")
        
        connectionFactory = mysql.MySQLConnectionFactory(username="foo", password="bar", hostname="localhost", db="mock")
        connection = connectionFactory.connect()

        del(sys.modules["MySQLdb"])

    def testConnectingToPostgresQLUsingDeprecatedConnectionFactory(self):
        sys.modules["pgdb"] = self.mock()
        sys.modules["pgdb"].expects(once()).method("connect")
        
        connectionFactory = postgresql.PgdbConnectionFactory(user="foo", password="bar", host="localhost", database="mock")
        connection = connectionFactory.connect()

        del(sys.modules["pgdb"])
        
    def testConnectingToSqliteUsingDeprecatedConnectionFactory(self):
        sys.modules["sqlite"] = self.mock()
        sys.modules["sqlite"].expects(once()).method("connect")
        
        connectionFactory = Sqlite.SqliteConnectionFactory(db="/tmp/foobar")
        connection = connectionFactory.connect()

        del(sys.modules["sqlite"])

    def testConnectingToMySql(self):
        sys.modules["MySQLdb"] = self.mock()
        sys.modules["MySQLdb"].expects(once()).method("connect")
        
        connectionFactory = factory.MySQLConnectionFactory(username="foo", password="bar", hostname="localhost", db="mock")
        connection = connectionFactory.connect()

        del(sys.modules["MySQLdb"])

    def testConnectingToPostgresQL(self):
        sys.modules["pgdb"] = self.mock()
        sys.modules["pgdb"].expects(once()).method("connect")
        
        connectionFactory = factory.PgdbConnectionFactory(user="foo", password="bar", host="localhost", database="mock")
        connection = connectionFactory.connect()

        del(sys.modules["pgdb"])
        
    def testConnectingToSqlite(self):
        sys.modules["sqlite"] = self.mock()
        sys.modules["sqlite"].expects(once()).method("connect")
        
        connectionFactory = factory.SqliteConnectionFactory(db="/tmp/foobar")
        connection = connectionFactory.connect()

        del(sys.modules["sqlite"])


    def testConnectingToOracle(self):
        sys.modules["cx_Oracle"] = self.mock()
        sys.modules["cx_Oracle"].expects(once()).method("connect")
        
        connectionFactory = factory.cxoraConnectionFactory(username="foo", password="bar", hostname="localhost", db="mock")
        connection = connectionFactory.connect()

        del(sys.modules["cx_Oracle"])

    def testQueryingOracleWithInvalidlyFormattedArguments(self):
        sys.modules["cx_Oracle"] = self.mock()
        sys.modules["cx_Oracle"].expects(once()).method("connect")
        
        connectionFactory = factory.cxoraConnectionFactory(username="foo", password="bar", hostname="localhost", db="mock")
        dt = DatabaseTemplate(connectionFactory)

        self.assertRaises(InvalidArgumentType, dt.query, """ 
                SELECT
                    impcarrcfg.paystat_work_dir, 
                    impcarrcfg.paystat_reload_dir,
                    impcarrcfg.paystat_archive_dir,
                    impcarrcfg.oid 
                FROM impcarrcfg, carr, lklabelsys 
                WHERE (lklabelsys.oid = impcarrcfg.lklabelsys_oid)
                and (carr.oid = impcarrcfg.carr_oid )
                and (carr.oid = ? and lklabelsys.oid = ?) 
            """, (5, 5), testSupportClasses.ImpFilePropsRowCallbackHandler())

        del(sys.modules["cx_Oracle"])

    def testQueryingOracleWithValidlyFormattedArguments(self):
        cursor = self.mock()
        cursor.expects(once()).method("execute")
        cursor.expects(once()).method("fetchall").will(return_value([("workDir", "reloadDir", "archiveDir", "oid1")]))

        conn = self.mock()
        conn.expects(once()).method("cursor").will(return_value(cursor))

        sys.modules["cx_Oracle"] = self.mock()
        sys.modules["cx_Oracle"].expects(once()).method("connect").will(return_value(conn))
        
        connectionFactory = factory.cxoraConnectionFactory(username="foo", password="bar", hostname="localhost", db="mock")
        dt = DatabaseTemplate(connectionFactory)

        dt.query(""" 
                SELECT
                    impcarrcfg.paystat_work_dir, 
                    impcarrcfg.paystat_reload_dir,
                    impcarrcfg.paystat_archive_dir,
                    impcarrcfg.oid 
                FROM impcarrcfg, carr, lklabelsys 
                WHERE (lklabelsys.oid = impcarrcfg.lklabelsys_oid)
                and (carr.oid = impcarrcfg.carr_oid )
                and (carr.oid = :carr_oid and lklabelsys.oid = :lklabelsys_oid) 
            """,
            {'carr_oid':5, 'lklabelsys_oid':5},
            testSupportClasses.ImpFilePropsRowCallbackHandler())

        del(sys.modules["cx_Oracle"])

class DatabaseTemplateMockTestCase(MockTestCase):
    """Testing the DatabaseTemplate utilizes stubbing and mocking, in order to isolate from different
    vendor implementations. This reduces the overhead in making changes to core functionality."""

    def setUp(self):
        self.mock = self.mock()
        connectionFactory = testSupportClasses.StubDBFactory()
        connectionFactory.stubConnection.mockCursor = self.mock
        self.databaseTemplate = DatabaseTemplate(connectionFactory)

    def testProgrammaticallyInstantiatingAnAbstractDatabaseTemplate(self):
        emptyTemplate = DatabaseTemplate()
        self.assertRaises(AttributeError, emptyTemplate.query, "sql query shouldn't work", None)

    def testProgrammaticHandlingInvalidRowHandler(self):
        self.mock.expects(once()).method("execute")
        self.mock.expects(once()).method("fetchall").will(return_value([("me", "myphone")]))
        
        self.assertRaises(AttributeError, self.databaseTemplate.query, "select * from foobar", rowhandler=testSupportClasses.InvalidCallbackHandler())
        
    def testProgrammaticHandlingImproperRowHandler(self):
        self.mock.expects(once()).method("execute")
        self.mock.expects(once()).method("fetchall").will(return_value([("me", "myphone")]))

        self.assertRaises(TypeError, self.databaseTemplate.query, "select * from foobar", rowhandler=testSupportClasses.ImproperCallbackHandler())
        
    def testProgrammaticHandlingValidDuckTypedRowHandler(self):
        self.mock.expects(once()).method("execute")
        self.mock.expects(once()).method("fetchall").will(return_value([("me", "myphone")]))

        results = self.databaseTemplate.query("select * from foobar", rowhandler=testSupportClasses.ValidHandler())

    def testIoCGeneralQuery(self):
        appContext = XmlApplicationContext("support/databaseTestApplicationContext.xml")
        mockConnectionFactory = appContext.getComponent("mockConnectionFactory")
        mockConnectionFactory.stubConnection.mockCursor = self.mock
        
        self.mock.expects(once()).method("execute")
        self.mock.expects(once()).method("fetchall").will(return_value([("me", "myphone")]))
        

        databaseTemplate = DatabaseTemplate(connectionFactory = mockConnectionFactory)
        results = databaseTemplate.query("select * from foobar", rowhandler=testSupportClasses.SampleRowCallbackHandler())
        
    def testProgrammaticStaticQuery(self):
        self.assertRaises(ArgumentMustBeNamed, self.databaseTemplate.query, "select * from animal", testSupportClasses.AnimalRowCallbackHandler())

        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([('snake', 'reptile', 1), ('racoon', 'mammal', 1)])).id("#2").after("#1")

        animalList = self.databaseTemplate.query("select * from animal", rowhandler=testSupportClasses.AnimalRowCallbackHandler())
        self.assertEquals(animalList[0].name, "snake")
        self.assertEquals(animalList[0].category, "reptile")
        self.assertEquals(animalList[1].name, "racoon")
        self.assertEquals(animalList[1].category, "mammal")
        
    def testProgrammaticQueryWithBoundArguments(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([('snake', 'reptile', 1)])).id("#2").after("#1")
        self.mock.expects(once()).method("execute").id("#3").after("#2")
        self.mock.expects(once()).method("fetchall").will(return_value([('snake', 'reptile', 1)])).id("#4").after("#3")

        animalList = self.databaseTemplate.query("select * from animal where name = %s", ("snake",), testSupportClasses.AnimalRowCallbackHandler())
        self.assertEquals(animalList[0].name, "snake")
        self.assertEquals(animalList[0].category, "reptile")

        animalList = self.databaseTemplate.query("select * from animal where name = ?", ("snake",), testSupportClasses.AnimalRowCallbackHandler())
        self.assertEquals(animalList[0].name, "snake")
        self.assertEquals(animalList[0].category, "reptile")
        
    def testProgrammaticStaticQueryForList(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([('snake', 'reptile', 1), ('racoon', 'mammal', 1)])).id("#2").after("#1")

        animalList = self.databaseTemplate.queryForList("select * from animal")
        self.assertEquals(animalList[0][0], "snake")
        self.assertEquals(animalList[0][1], "reptile")
        self.assertEquals(animalList[1][0], "racoon")
        self.assertEquals(animalList[1][1], "mammal")
        
    def testProgrammaticQueryForListWithBoundArguments(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([('snake', 'reptile', 1)])).id("#2").after("#1")
        self.mock.expects(once()).method("execute").id("#3").after("#2")
        self.mock.expects(once()).method("fetchall").will(return_value([('snake', 'reptile', 1)])).id("#4").after("#3")

        animalList = self.databaseTemplate.queryForList("select * from animal where name = %s", ("snake",))
        self.assertEquals(animalList[0][0], "snake")
        self.assertEquals(animalList[0][1], "reptile")
        
        animalList = self.databaseTemplate.queryForList("select * from animal where name = ?", ("snake",))
        self.assertEquals(animalList[0][0], "snake")
        self.assertEquals(animalList[0][1], "reptile")

    def testProgrammaticQueryForListWithBoundArgumentsNotProperlyTuplized(self):
        self.assertRaises(InvalidArgumentType, self.databaseTemplate.queryForList, "select * from animal where name = %s", "snake")
        self.assertRaises(InvalidArgumentType, self.databaseTemplate.queryForList, "select * from animal where name = ?", "snake")

    def testProgrammaticStaticQueryForInt(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([(1,)])).id("#2").after("#1")

        count = self.databaseTemplate.queryForInt("select population from animal where name = 'snake'")
        self.assertEquals(count, 1)
        
    def testProgrammaticQueryForIntWithBoundArguments(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([(1,)])).id("#2").after("#1")
        self.mock.expects(once()).method("execute").id("#3").after("#2")
        self.mock.expects(once()).method("fetchall").will(return_value([(1,)])).id("#4").after("#3")

        count = self.databaseTemplate.queryForInt("select population from animal where name = %s", ("snake",))
        self.assertEquals(count, 1)

        count = self.databaseTemplate.queryForInt("select population from animal where name = ?", ("snake",))
        self.assertEquals(count, 1)
        
    def testProgrammaticStaticQueryForLong(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([(4,)])).id("#2").after("#1")

        count = self.databaseTemplate.queryForObject("select count(*) from animal", requiredType=types.IntType)
        self.assertEquals(count, 4)
        
    def testProgrammaticQueryForLongWithBoundVariables(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([(1,)])).id("#2").after("#1")
        self.mock.expects(once()).method("execute").id("#3").after("#2")
        self.mock.expects(once()).method("fetchall").will(return_value([(1,)])).id("#4").after("#3")

        count = self.databaseTemplate.queryForObject("select count(*) from animal where name = %s", ("snake",), types.IntType)
        self.assertEquals(count, 1)

        count = self.databaseTemplate.queryForObject("select count(*) from animal where name = ?", ("snake",), types.IntType)
        self.assertEquals(count, 1)
        
    def testProgrammaticStaticQueryForObject(self):
        self.assertRaises(ArgumentMustBeNamed, self.databaseTemplate.queryForObject, "select name from animal where category = 'reptile'", types.StringType)

        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([("snake",)])).id("#2").after("#1")

        name = self.databaseTemplate.queryForObject("select name from animal where category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "snake")
        
    def testProgrammaticQueryForObjectWithBoundVariables(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([("snake",)])).id("#2").after("#1")
        self.mock.expects(once()).method("execute").id("#3").after("#2")
        self.mock.expects(once()).method("fetchall").will(return_value([("snake",)])).id("#4").after("#3")

        name = self.databaseTemplate.queryForObject("select name from animal where category = %s", ("reptile",), types.StringType)
        self.assertEquals(name, "snake")

        name = self.databaseTemplate.queryForObject("select name from animal where category = ?", ("reptile",), types.StringType)
        self.assertEquals(name, "snake")
        
    def testProgrammaticStaticUpdate(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("execute").id("#2").after("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([("python",)])).id("#3").after("#2")
        self.mock.rowcount = 1

        rows = self.databaseTemplate.update("UPDATE animal SET name = 'python' WHERE name = 'snake'")
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "python")
        
    def testProgrammaticUpdateWithBoundVariables(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("execute").id("#2").after("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([("python",)])).id("#3").after("#2")
        self.mock.expects(once()).method("execute").id("#4").after("#3")
        self.mock.expects(once()).method("execute").id("#5").after("#4")
        self.mock.expects(once()).method("fetchall").will(return_value([("coily",)])).id("#6").after("#5")
        self.mock.rowcount = 1

        rows = self.databaseTemplate.update("UPDATE animal SET name = ? WHERE category = ?", ("python", "reptile"))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "python")

        rows = self.databaseTemplate.update("UPDATE animal SET name = ? WHERE category = %s", ("coily", "reptile"))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "coily")

    def testProgrammaticStaticInsert(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("execute").id("#2").after("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([("black mamba",)])).id("#3").after("#2")
        self.mock.rowcount = 1

        rows = self.databaseTemplate.execute ("INSERT INTO animal (name, category, population) VALUES ('black mamba', 'kill_bill_viper', 1)")
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'kill_bill_viper'", requiredType=types.StringType)
        self.assertEquals(name, "black mamba")
        
    def testProgrammaticInsertWithBoundVariables(self):
        self.mock.expects(once()).method("execute").id("#1")
        self.mock.expects(once()).method("execute").id("#2").after("#1")
        self.mock.expects(once()).method("fetchall").will(return_value([("black mamba",)])).id("#3").after("#2")
        self.mock.expects(once()).method("execute").id("#4").after("#3")
        self.mock.expects(once()).method("execute").id("#5").after("#4")
        self.mock.expects(once()).method("fetchall").will(return_value([("cottonmouth",)])).id("#6").after("#5")
        self.mock.rowcount = 1
        
        rows = self.databaseTemplate.execute ("INSERT INTO animal (name, category, population) VALUES (?, ?, ?)", ('black mamba', 'kill_bill_viper', 1))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'kill_bill_viper'", requiredType=types.StringType)
        self.assertEquals(name, "black mamba")

        rows = self.databaseTemplate.execute("INSERT INTO animal (name, category, population) VALUES (%s, %s, %s)", ('cottonmouth', 'kill_bill_viper', 1))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("select name from animal where name = 'cottonmouth'", requiredType=types.StringType)
        self.assertEquals(name, "cottonmouth")

class AbstractDatabaseTemplateTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.factory = None
        self.createdTables = False

    def setUp(self):
        if not self.createdTables:
            self.createTables()
        self.databaseTemplate = DatabaseTemplate(self.factory)
        self.databaseTemplate.execute("DELETE FROM animal")
        self.factory.commit()
        self.assertEquals(len(self.databaseTemplate.queryForList("SELECT * FROM animal")), 0)
        self.databaseTemplate.execute("INSERT INTO animal (name, category, population) VALUES ('snake', 'reptile', 1)")
        self.databaseTemplate.execute("INSERT INTO animal (name, category, population) VALUES ('racoon', 'mammal', 0)")
        self.databaseTemplate.execute ("INSERT INTO animal (name, category, population) VALUES ('black mamba', 'kill_bill_viper', 1)")
        self.databaseTemplate.execute ("INSERT INTO animal (name, category, population) VALUES ('cottonmouth', 'kill_bill_viper', 1)")
        self.factory.commit()
        self.assertEquals(len(self.databaseTemplate.queryForList("SELECT * FROM animal")), 4)

    def tearDown(self):
        self.factory.rollback()

    def testProgrammaticallyInstantiatingAnAbstractDatabaseTemplate(self):
        emptyTemplate = DatabaseTemplate()
        self.assertRaises(AttributeError, emptyTemplate.query, "sql query shouldn't work", None)

    def testProgrammaticHandlingInvalidRowHandler(self):
        self.assertRaises(AttributeError, self.databaseTemplate.query, "select * from animal", rowhandler=testSupportClasses.InvalidCallbackHandler())

    def testProgrammaticHandlingImproperRowHandler(self):
        self.assertRaises(TypeError, self.databaseTemplate.query, "select * from animal", rowhandler=testSupportClasses.ImproperCallbackHandler())
        
    def testProgrammaticHandlingValidDuckTypedRowHandler(self):
        results = self.databaseTemplate.query("select * from animal", rowhandler=testSupportClasses.ValidHandler())

    def testProgrammaticStaticQuery(self):
        self.assertRaises(ArgumentMustBeNamed, self.databaseTemplate.query, "select * from animal", testSupportClasses.AnimalRowCallbackHandler())

        animalList = self.databaseTemplate.query("select name, category from animal", rowhandler=testSupportClasses.AnimalRowCallbackHandler())
        self.assertEquals(animalList[0].name, "snake")
        self.assertEquals(animalList[0].category, "reptile")
        self.assertEquals(animalList[1].name, "racoon")
        self.assertEquals(animalList[1].category, "mammal")
        
    def testProgrammaticQueryWithBoundArguments(self):
        animalList = self.databaseTemplate.query("select name, category from animal where name = %s", ("snake",), testSupportClasses.AnimalRowCallbackHandler())
        self.assertEquals(animalList[0].name, "snake")
        self.assertEquals(animalList[0].category, "reptile")

        animalList = self.databaseTemplate.query("select name, category from animal where name = ?", ("snake",), testSupportClasses.AnimalRowCallbackHandler())
        self.assertEquals(animalList[0].name, "snake")
        self.assertEquals(animalList[0].category, "reptile")
        
    def testProgrammaticStaticQueryForList(self):
        animalList = self.databaseTemplate.queryForList("select name, category from animal")
        self.assertEquals(animalList[0][0], "snake")
        self.assertEquals(animalList[0][1], "reptile")
        self.assertEquals(animalList[1][0], "racoon")
        self.assertEquals(animalList[1][1], "mammal")
        
    def testProgrammaticQueryForListWithBoundArguments(self):
        animalList = self.databaseTemplate.queryForList("select name, category from animal where name = %s", ("snake",))
        self.assertEquals(animalList[0][0], "snake")
        self.assertEquals(animalList[0][1], "reptile")
        
        animalList = self.databaseTemplate.queryForList("select name, category from animal where name = ?", ("snake",))
        self.assertEquals(animalList[0][0], "snake")
        self.assertEquals(animalList[0][1], "reptile")

    def testProgrammaticQueryForListWithBoundArgumentsNotProperlyTuplized(self):
        self.assertRaises(InvalidArgumentType, self.databaseTemplate.queryForList, "select * from animal where name = %s", "snake")
        self.assertRaises(InvalidArgumentType, self.databaseTemplate.queryForList, "select * from animal where name = ?", "snake")

    def testProgrammaticStaticQueryForInt(self):
        count = self.databaseTemplate.queryForInt("select population from animal where name = 'snake'")
        self.assertEquals(count, 1)
        
    def testProgrammaticQueryForIntWithBoundArguments(self):
        count = self.databaseTemplate.queryForInt("select population from animal where name = %s", ("snake",))
        self.assertEquals(count, 1)

        count = self.databaseTemplate.queryForInt("select population from animal where name = ?", ("snake",))
        self.assertEquals(count, 1)
        
    def testProgrammaticStaticQueryForLong(self):
        count = self.databaseTemplate.queryForObject("select count(*) from animal", requiredType=self.factory.countType())
        self.assertEquals(count, 4)
        
    def testProgrammaticQueryForLongWithBoundVariables(self):
        count = self.databaseTemplate.queryForObject("select count(*) from animal where name = %s", ("snake",), self.factory.countType())
        self.assertEquals(count, 1)

        count = self.databaseTemplate.queryForObject("select count(*) from animal where name = ?", ("snake",), self.factory.countType())
        self.assertEquals(count, 1)
        
    def testProgrammaticStaticQueryForObject(self):
        self.assertRaises(ArgumentMustBeNamed, self.databaseTemplate.queryForObject, "select name from animal where category = 'reptile'", types.StringType)

        name = self.databaseTemplate.queryForObject("select name from animal where category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "snake")
        
    def testProgrammaticQueryForObjectWithBoundVariables(self):
        name = self.databaseTemplate.queryForObject("select name from animal where category = %s", ("reptile",), types.StringType)
        self.assertEquals(name, "snake")

        name = self.databaseTemplate.queryForObject("select name from animal where category = ?", ("reptile",), types.StringType)
        self.assertEquals(name, "snake")
        
    def testProgrammaticStaticUpdate(self):
        rows = self.databaseTemplate.update("UPDATE animal SET name = 'python' WHERE name = 'snake'")
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "python")
        
    def testProgrammaticUpdateWithBoundVariables(self):
        rows = self.databaseTemplate.update("UPDATE animal SET name = ? WHERE category = ?", ("python", "reptile"))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "python")

        rows = self.databaseTemplate.update("UPDATE animal SET name = ? WHERE category = %s", ("coily", "reptile"))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'reptile'", requiredType=types.StringType)
        self.assertEquals(name, "coily")

    def testProgrammaticStaticInsert(self):
        self.databaseTemplate.execute("DELETE FROM animal")
        rows = self.databaseTemplate.execute ("INSERT INTO animal (name, category, population) VALUES ('black mamba', 'kill_bill_viper', 1)")
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'kill_bill_viper'", requiredType=types.StringType)
        self.assertEquals(name, "black mamba")
        
    def testProgrammaticInsertWithBoundVariables(self):
        self.databaseTemplate.execute("DELETE FROM animal")
        rows = self.databaseTemplate.execute ("INSERT INTO animal (name, category, population) VALUES (?, ?, ?)", ('black mamba', 'kill_bill_viper', 1))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("SELECT name FROM animal WHERE category = 'kill_bill_viper'", requiredType=types.StringType)
        self.assertEquals(name, "black mamba")

        rows = self.databaseTemplate.execute("INSERT INTO animal (name, category, population) VALUES (%s, %s, %s)", ('cottonmouth', 'kill_bill_viper', 1))
        self.assertEquals(rows, 1)

        name = self.databaseTemplate.queryForObject("select name from animal where name = 'cottonmouth'", requiredType=types.StringType)
        self.assertEquals(name, "cottonmouth")

class MySQLDatabaseTemplateTestCase(AbstractDatabaseTemplateTestCase):
    def __init__(self, methodName='runTest'):
        AbstractDatabaseTemplateTestCase.__init__(self, methodName)

    def createTables(self):
        self.createdTables = True
        try:
            self.factory = factory.MySQLConnectionFactory("springpython", "springpython", "localhost", "springpython")
            dt = DatabaseTemplate(self.factory)
            dt.execute("DROP TABLE IF EXISTS animal")
            dt.execute("""
                CREATE TABLE animal (
                  id serial PRIMARY KEY,
                  name VARCHAR(11),
                  category VARCHAR(20),
                  population SMALLINT
                ) ENGINE=innodb
            """)
            self.factory.commit()

        except Exception, e:
            print("""
                !!! Can't run MySQLDatabaseTemplateTestCase !!!

                This assumes you have executed some step like:
                % sudo apt-get install mysql (Ubuntu)
                % apt-get install mysql (Debian)

                And then created a database for the spring python user:
                % mysql -uroot
                mysql> DROP DATABASE IF EXISTS springpython;
                mysql> CREATE DATABASE springpython;
                mysql> GRANT ALL ON springpython.* TO springpython@localhost IDENTIFIED BY 'springpython';

                That should setup the springpython user to be able to create tables as needed for these test cases.
            """)
            raise e

    def testIoCGeneralQuery(self):
        appContext = XmlApplicationContext("support/databaseTestMySQLApplicationContext.xml")
        factory = appContext.getComponent("connectionFactory")
        
        databaseTemplate = DatabaseTemplate(factory)
        results = databaseTemplate.query("select * from animal", rowhandler=testSupportClasses.SampleRowCallbackHandler())
        
class PostGreSQLDatabaseTemplateTestCase(AbstractDatabaseTemplateTestCase):
    def __init__(self, methodName='runTest'):
        AbstractDatabaseTemplateTestCase.__init__(self, methodName)

    def createTables(self):
        self.createdTables = True
        try:
            self.factory = factory.PgdbConnectionFactory("springpython", "springpython", "localhost", "springpython")
            dt = DatabaseTemplate(self.factory)
            dt.execute("DROP TABLE IF EXISTS animal")
            dt.execute("""
                CREATE TABLE animal (
                  id serial PRIMARY KEY,
                  name VARCHAR(11),
                  category VARCHAR(20),
                  population integer
                )
            """)
            self.factory.commit()

        except Exception, e:
            print("""
                !!! Can't run PostGreSQLDatabaseTemplateTestCase !!!

                This assumes you have executed some step like:
                % sudo apt-get install postgresql (Ubuntu)
                % apt-get install postgresql (Debian)

                Next, you need to let PostGreSQL's accounts be decoupled from the system accounts.
                Find pg_hba.conf underneath /etc and add something like this:
                # TYPE  DATABASE    USER        IP-ADDRESS        IP-MASK           METHOD
                host    all         all         <your network>    <yournetworkmask>    md5

                Then, restart it.
                % sudo /etc/init.d/postgresql restart (Ubuntu)

                Then create a user database to match this account.
                % sudo -u postgres psql -f support/setupPostGreSQLSpringPython.sql

                From here on, you should be able to connect into PSQL and run SQL scripts.
            """)
            raise e

    def testIoCGeneralQuery(self):
        appContext = XmlApplicationContext("support/databaseTestPGApplicationContext.xml")
        factory = appContext.getComponent("connectionFactory")
        
        databaseTemplate = DatabaseTemplate(factory)
        results = databaseTemplate.query("select * from animal", rowhandler=testSupportClasses.SampleRowCallbackHandler())

class SqliteDatabaseTemplateTestCase(AbstractDatabaseTemplateTestCase):
    def __init__(self, methodName='runTest'):
        AbstractDatabaseTemplateTestCase.__init__(self, methodName)

    def createTables(self):
        self.createdTables = True
        try:
            try:
                os.remove("/tmp/springpython.db")
            except OSError:
                pass
            self.factory = factory.SqliteConnectionFactory("/tmp/springpython.db")
            dt = DatabaseTemplate(self.factory)

            dt.execute("""
                CREATE TABLE animal (
                  id serial PRIMARY KEY,
                  name VARCHAR(11),
                  category VARCHAR(20),
                  population integer
                )
            """)
            self.factory.commit()

        except Exception, e:
            print("""
                !!! Can't run SqliteDatabaseTemplateTestCase !!!
            """)
            raise e

    def testIoCGeneralQuery(self):
        appContext = XmlApplicationContext("support/databaseTestSqliteApplicationContext.xml")
        factory = appContext.getComponent("connectionFactory")
        
        databaseTemplate = DatabaseTemplate(factory)
        results = databaseTemplate.query("select * from animal", rowhandler=testSupportClasses.SampleRowCallbackHandler())

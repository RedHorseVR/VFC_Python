#use
	
	use File::stat qw(stat);
	
sub LoadFileAsString {
	local ( $file ) = @_;
	local ( $keyfile ) ;
	open( FILE, $file );
	while(<FILE>) {
		s/^ *\n//;
		tr/\t/ /;
		$keyfile = "$keyfile$_";
		}
	
	close ( FILE );
	$keyfile; }
# main
	$cmd_line = $ENV{'QUERY_STRING'} ;
	
	($cmd_line) = @ARGV;
	
	$outputVFC =  "$cmd_line.vfc" ;
	$file = $cmd_line ;
	print( STDOUT  "parse file =  $cmd_line  ...  \n" );
	$lasttime = 0;
	$I = 2;
	Parse();
	while( $I < 1 ) {
		$I = $I+1;
		$nowtime = stat($file)->mtime;
		
		
		if ( $nowtime != $lasttime )
		{
			Parse();
			$lasttime = stat($file)->mtime;
			print( STDOUT  "\nlistening and autoparse for file =  $cmd_line  ...  \n" );
		}else{
			}
		
		select(undef, undef, undef, 0.25);
		}
	
	print "done\n";
	
sub PrintTabs{ local ( $num ) = @_;
	local( $i ) = 0;
	while(  $i  < $num ) {
		print( "\t|" );
		$i=$i+1;}
	
	}
my @stack;
sub PrintStack{
	
	
	print "";
	PrintTabs(10);
	print "-------- STACK:-------\n";
	foreach $val (@stack){
		$val =~ s/\t*//g;
		$val =~ s/^ +//g;
		PrintTabs(10);
		print( "$val\n" );
		}
	
	PrintTabs(10);
	print "^----------------^\n";
	}
sub Flow{ local ( $lastCode ) = @_;
	$Flow = (     $lastCode =~m/$INPUT/     ||   $lastCode =~m/$LOOP/     ||   $lastCode =~m/$BRANCH/    ||  $lastCode =~ m/$EVENT/ )  ;
	return 1; }
sub getCode { local ( $code ) = @_;
	$code  =~ s/\n// ;
	$code =~ s/    //g ;
	$code =~ s/#.*$//;
	return $code ; }
sub getComment { local ( $comment ) = @_;
	if ( $comment =~ m/^.*#{1}/  )
	{
		$comment =~ s/^.*#{1}//;
	}else{
		$comment ="" ;
		}
	return $comment; }
sub NumTabs{
	local($match) = @_;
	
	$num = 0 ;
	while( $match =~ m/^\t/  ) {
		$match =~ s/\t//;
		$num = $num + 1 ;
		}
	
	return  $num  ;
}
sub getIndents { local ( $Line ) = @_;
	local( $count )  = 0 ;
	while( $Line =~ m/    / ) {
		$count = $count + 1 ;
		$Line =~ s/    /T/ ;
		
		}
	
	if ( $Line =~ m/Telse:/  ||   $Line =~ m/T\):/   )
	{
		$count = $count + 1;
		
		}
	return $count; }
sub GetToken{ local( $LEVEL, $PREV_LEVEL, $CODE , $PREV_CODE ) = @_;
$BRANCH = "(if|try)";
$INPUT = "(def|class)";

$LOOP = "^\t*(for|while|do)";
$WITH = "^\t*(with)";
$PEND = "^\t*(else|except)";
$END = "^\t*(break|continue|return)";
$OUTPUT = "^\t*(print)";
$EVENT = "^(import|from)";
$PATH = "^\t*(else|elif)";
local( $DIFF )  = $LEVEL - $PREV_LEVEL ;
local( $TYPE ) = "...";
local( $TOKEN ) = "...";
if ($DIFF > 0  )
{
	if ( $PREV_CODE =~m/$INPUT/ )
	{
		$TYPE = "end( );\/\/$PREV_LINE " ;
		$TOKEN = "input( $PREV_CODE);\/\/  LEVEL($PREV_LEVEL)  "  ;
	} else {
		if ( $PREV_CODE =~ m/$BRANCH/ )
		{
			$TYPE = "bend(  );\/\/  $PREV_LINE " ;
			$TOKEN = "branch( $PREV_CODE);\/\/  LEVEL($PREV_LEVEL)  "  ;
		} else {
			$TYPE = "set( );\/\/$PREV_LINE " ;
			$TOKEN = "set( $PREV_CODE);\/\/  LEVEL($PREV_LEVEL)  "  ;
			}
		}
	push( @stack, "$TYPE <<<$PREV_CODE"  );
	
} else {
	if ($DIFF <  0  )
	{
		$POP = pop( @stack ) ;
		
		$TOKEN = "$POP  <---- popped"  ;
	} else {
		$TOKEN = ""  ;
		if ( $CODE =~ m/$PATH/ )
		{
			$TOKEN = "path( $CODE);\/\/  LEVEL($LEVEL)  "  ;
		} else {
			$TOKEN = "set( $CODE);\/\/  LEVEL($LEVEL)  "  ;
			}
		}
	}
if ( $DIFF * $DIFF  > 1 )
{
	$TOKEN = "$TOKEN <---! ERROR IN DIFF = $DIFF "  ;
} else {
	}
return $TOKEN;  }
sub print_extra_TOKENS{ local( $TOKEN ) = @_;
$BRANCH_CLOSE = "<<<$BRANCH";
$INPUT_CLOSE = "<(def|class)";

if ( $TOKEN =~m/^input\(/ )
{
	print( "branch( );\/\/x\n" );
	print( "path( );\/\/x\n" );
	print( "path( );\/\/x\n" );
} else {
	if ( $TOKEN =~m/$INPUT_CLOSE/ )
	{
		print( "bend( );\/\/x\n" );
	} else {
		
		}
	}
return ;}
sub Parse{
	open OUTFILE,  ">" ,   $outputVFC  or die "Cannot open output: $!";
	open( FILE, $cmd_line );
	print( "...parseing $cmd_line\n" );
	$lastCount = 0;
	$ParsedFile  = "";
	$multiLine = 0;
	$LINE = 0;
	$PREV_LEVEL = 0;
	$PREV_LINE = 0;
	$LEVEL = 0;
	local($DIFF) = 0;
	while(<FILE>) {
		$LINE = $LINE + 1 ;
		if (     ( $_ =~m/\"\"\"/   || $_ =~m/\'\'\'/)   )
		{
			$multiLine = ~$multiLine;
			}
		if ( $_ =~ m/^\n$/  ||  $multiLine )
		{
			if ( $multiLine )
			{
				$LEVEL = 0;
				print( "set( );\/\/ $_" );
			} else {
				print( "set();\/\/ $LINE\n" );
				}
		}else{
			
			
			$LEVEL = getIndents( $_  ) ;
			$COMM = getComment( $_ ) ;
			$CODE = getCode( $_ ) ;
			$DIFF = $PREV_LEVEL -  $LEVEL ;
			if ( $DIFF   > 1   )
			{
				while( $DIFF > -1  ) {
					$DIFF =  $DIFF -1 ;
					$BACK_LEVEL  =  $LEVEL + $DIFF;
					$BACK_DIFF  =  $BACK_LEVEL - $PREV_LEVEL ;
					$TOKEN = GetToken( $BACK_LEVEL, $PREV_LEVEL , $CODE , $PREV_CODE );
					print_extra_TOKENS( $TOKEN );
					print( "$TOKEN\n" );
					
					}
				
			}else{
				print( "set($CODE);\/\/<<<<<<<<\n" );
				$TOKEN = GetToken( $LEVEL, $PREV_LEVEL , $CODE , $PREV_CODE );
				print("$TOKEN \n" ) ;
				print_extra_TOKENS( $TOKEN );
				}
			}
		$PREV_LEVEL = $LEVEL;
		$PREV_LINE = $LINE;
		$PREV_CODE = $CODE;
		}
	
	close ( FILE );
	close ( OUTFILE );
	}
sub printFooter{
	$rootfile = $file;
	$rootfile =~ s/^.*\\//;
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED SESSION INFORMATION\n" );
	print( OUTFILE  "; 255 16777215 65280 16777088 16711680 255 8388608 0 255 255 65535 65280 4210688 \n");
	print( OUTFILE  "$rootfile.py   #\"\"\"  #\"\"\"  \n");
	print( OUTFILE  "; notepad++.exe \n");
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED ALTSESSION INFORMATION\n");
	print( OUTFILE  "; 262 123 765 1694 0 170   379   4294966903    python.key  0");
	}
#  Export  Date: 08:09:07 PM - 27:Apr:2023.


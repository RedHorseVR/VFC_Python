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
sub getComment { local ( $comment ) = @_;
	$comment  =~ s/\n// ;
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
sub GetToken{ local( $LEVEL, $PREV_LEVEL, $CODE , $PREV_CODE , $DIFF  ) = @_;
$BRANCH = "(if|try)";
$INPUT = "(def|class)";

$LOOP = "^\t*(for|while|do)";
$WITH = "^\t*(with)";
$PEND = "^\t*(else|except)";
$END = "^\t*(break|continue|return)";
$OUTPUT = "^\t*(print)";
$EVENT = "^(import|from)";
$PATH = "^\t*(else|elif)";
$DIFF = $LEVEL - $PREV_LEVEL ;
local( $TYPE ) = "...";
local( $TOKEN ) = "...";
if ($DIFF > 0  )
{
	$TOKEN = "push -->  $PREV_CODE LEVEL($PREV_LEVEL) "  ;
	if ( $PREV_CODE =~m/$INPUT/ )
	{
		$TYPE = "end( );\/\/" ;
	} else {
		if ( $PREV_CODE =~ m/$BRANCH/ )
		{
			$TYPE = "bend( $PREV_LINE  );\/\/" ;
			}
		}
	push( @stack, "$TYPE <--- $PREV_CODE"  );
} else {
	if ($DIFF <  0  )
	{
		$POP = pop( @stack ) ;
		$TOKEN = "pop <--  from   $POP  "  ;
	} else {
		$TOKEN = ""  ;
		}
	}
if ( $DIFF * $DIFF  > 1 )
{
	$TOKEN = "$TOKEN <---! ERROR IN DIFF = $DIFF "  ;
} else {
	}
return $TOKEN;  }
sub getCode { local ( $code ) = @_;
	$code  =~ s/\n// ;
	$code =~ s/    //g ;
	$code =~ s/#.*$//;
	return $code ; }
sub peek { local( @stack ) = @_ ;
	local( $ret ) = pop( @stack );
	push( @stack , $ret  );
	if ( $ret eq ""  )
	{
		$ret = -1;
	}else{
		}
	return $ret ;
}
sub getType{ local( $CODE , $LEVEL    ) = @_;
my $BRANCH = "^(if|try)";
my $INPUT = "^(def|class)";
my $OUTPUT = "^(print)";
my $PATH = "^(else|elif|except|final)";

$level = peek( @levelstack );
if ( $level == $LEVEL   )
{
	
	pop( @levelstack ) ;
	print( pop( @typestack ) ) ;
}else{
	
	}

local( $TYPE ) = "...";
if ( $CODE =~m/$INPUT/ )
{
	$TYPE = "\ninput( $CODE  );\nbranch();\npath();\npath();\/\/ > $LEVEL <" ;
	push( @typestack, "bend();\nend( );\/\/$CODE > $LEVEL\n" );
	push( @levelstack, $LEVEL );
} elsif ( $CODE =~ m/$BRANCH/ )  {
	$TYPE = "branch( $CODE );\/\/ > $LEVEL" ;
	push( @typestack, "bend( );\/\/$CODE \n" );
	push( @levelstack, $LEVEL );
} elsif ( $CODE =~ m/$OUTPUT/ )  {
	$TYPE = "output( $CODE );\/\/" ;
} elsif ( $CODE =~ m/$PATH/ )  {
	$TYPE = "path( $CODE );\/\/" ;
} else {
	$TYPE = "set( $CODE );\/\/" ;
	}
return $TYPE;  }
my @typestack;
my @levelstack;
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
	while(<FILE>) {
		$InLine = $_;
		$LINE = $LINE + 1 ;
		if (  $multiLine ==0 &&   (  $_ =~s/^ *\"\"\"//   || $_ =~s/^ *\'\'\'//   )   )
		{
			if  ( $_ =~s/\"\"\"//   || $_ =~s/\'\'\'// )
			{
				$COMM =  $_ ;
				$_ = ""  ;
			}else{
				$multiLine = 1 ;
				$_ = "BEGIN MULTI LINE COMMENT\n";
				}
		} else {
			$COMM = getComment( $_ ) ;
			}
		if ( $_ =~ m/^\n$/  ||  $multiLine )
		{
			if ( $multiLine )
			{
				
				if (    ( $_ =~m/\"\"\"/   || $_ =~m/\'\'\'/)   )
				{
					$multiLine = 0 ;
					$_ = "END MULTI LINE COMMENT\n";
					}
				print( "set( ):\/\/ $LINE ... $_" );
			} else {
				
				}
		}else{
			
			
			$LEVEL = getIndents( $_  ) ;
			$CODE = getCode( $InLine ) ;
			$MISSED_LEVELS = $PREV_LEVEL - $LEVEL;
			if ( $MISSED_LEVELS  > 1 )
			{
				
				$MISSED = 1;
				while( $MISSED_LEVELS >0 ) {
					$PROC_LEVEL = $PREV_LEVEL-$MISSED ;
					
					
					$TYPE = getType( "BLANK" , $PROC_LEVEL  ) ;
					
					$MISSED = $MISSED + 1 ;
					$MISSED_LEVELS = $MISSED_LEVELS  -1; }
				
				
			}else{
				
				}
			$TYPE = getType( $CODE , $LEVEL  ) ;
			print "$TYPE $COMM\n";
			}
		$PREV_LEVEL = $LEVEL;
		$PREV_LINE = $LINE;
		$PREV_CODE = $CODE;
		}
	
	close ( FILE );
	close ( OUTFILE );
	print( "\n$LINE processed lines\n" );
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
#  Export  Date: 12:46:41 AM - 28:Apr:2023.

